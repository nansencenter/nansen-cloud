import os

from django.db import models
from django.contrib.gis.db import models as geomodels
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.core.validators import URLValidator
from django.utils.translation import ugettext as _

from nansencloud.vocabularies.models import Parameter
from nansencloud.vocabularies.models import ScienceKeyword
from nansencloud.vocabularies.models import Platform
from nansencloud.vocabularies.models import Instrument
from nansencloud.vocabularies.models import ISOTopicCategory
from nansencloud.vocabularies.models import DataCenter
from nansencloud.vocabularies.models import Location as GCMDLocation
from nansencloud.vocabularies.models import HorizontalDataResolution
from nansencloud.vocabularies.models import VerticalDataResolution
from nansencloud.vocabularies.models import TemporalDataResolution

from nansencloud.catalog.managers import SourceManager
from nansencloud.catalog.managers import DatasetURIManager

class GeographicLocation(geomodels.Model):
    geometry = geomodels.GeometryField()

    objects = geomodels.GeoManager()

    def __str__(self):
        return str(self.geometry.geom_type) + str(self.geometry.num_points)


class Source(models.Model):
    platform = models.ForeignKey(Platform)
    instrument = models.ForeignKey(Instrument)
    specs = models.CharField(max_length=50, default='',
        help_text=_('Further specifications of the source.'))

    objects = SourceManager()

    class Meta:
        unique_together = (("platform", "instrument"),)

    def __str__(self):
        return '%s/%s' % (self.platform, self.instrument)

    def natural_key(self):
        return (self.platform.short_name, self.instrument.short_name)

class Personnel(models.Model):
    '''
    This class follows the fields specified in
    http://gcmd.nasa.gov/add/difguide/personnel.html, except those already
    present in django.contrib.auth.User
    We may use django-userena to handle Personnel and other users..
    '''
    phone = models.CharField(max_length=80)
    fax = models.CharField(max_length=80)
    address = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    province_or_state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=80)
    country = models.CharField(max_length=80)

    class Meta:
        permissions = (
                ("accessLevel0", "Can access all data"),
                ("accessLevel1", "Can access data at own data center"),
                ("accessLevel2", "Can access public data only"),
            )

class Role(models.Model):
    INVESTIGATOR = 'Investigator'
    TECH_CONTACT = 'Technical Contact' # I interpret this as the data center contact
    DIF_AUTHOR = 'DIF Author'
    ROLE_CHOICES = ((INVESTIGATOR, INVESTIGATOR), (TECH_CONTACT, TECH_CONTACT),
            (DIF_AUTHOR, DIF_AUTHOR))
    personnel = models.ForeignKey(Personnel)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

class Dataset(models.Model):
    ''' 
    The Dataset model contains fields from the GCMD DIF conventions that are
    used for indexing and search.

    For a full description of the DIF format, see
    http://gcmd.nasa.gov/add/difguide/index.html and
    http://gcmd.nasa.gov/add/difguide/WRITEADIF.pdf

    Fields:
    -------
    entry_title : CharField
    parameters: ManyToManyField to Parameter through DatasetParameter
    ISO_topic_category : ForeignKey to ISOTopicCategory
    data_center : ForeignKey to DataCenter
    summary : TextField
            In addition to some general information, the summary should also
            contain information about the project from/for which the data was
            collected/created
    source : ForeignKey to Source
            Contains information about the instrument and platform by which the
            data was collected
    time_coverage_start : DateTimeField
    time_coverage_end : DateTimeField
    geographic_location : ForeignKey to GeographicLocation
    gcmd_location : ForeignKey to vocabularies.models.Location
    access_constraints : CharField
            Determines the access level of the Dataset: Limited, In-house, or
            Public

    '''
    ACCESS_LEVEL0 = 'accessLevel0'
    ACCESS_LEVEL1 = 'accessLevel1'
    ACCESS_LEVEL2 = 'accessLevel2'
    ACCESS_CHOICES = (
            (ACCESS_LEVEL0, _('Limited')),
            (ACCESS_LEVEL1, _('In-house')),
            (ACCESS_LEVEL2, _('Public')),
        )

    # DIF required fields
    entry_title = models.CharField(max_length=220)
    parameters = models.ManyToManyField(Parameter, through='DatasetParameter')
    ISO_topic_category = models.ForeignKey(ISOTopicCategory)
    data_center = models.ForeignKey(DataCenter)
    summary = models.TextField()

    # DIF highly recommended fields
    source = models.ForeignKey(Source, blank=True, null=True)
    time_coverage_start = models.DateTimeField(blank=True, null=True)
    time_coverage_end = models.DateTimeField(blank=True, null=True)
    geographic_location = models.ForeignKey(GeographicLocation, blank=True, null=True)
    gcmd_location = models.ForeignKey(GCMDLocation, blank=True, null=True)
    access_constraints = models.CharField(max_length=50,
            choices=ACCESS_CHOICES, blank=True, null=True)

    def __str__(self):
        return '%s/%s/%s' % (self.source.platform, self.source.instrument,
                self.time_coverage_start.isoformat())

# Keep this for reference if we want to add it
#class DataResolution(models.Model):
#    dataset = models.ForeignKey(Dataset)
#    latitude_resolution = models.CharField(max_length=50)
#    longitude_resolution = models.CharField(max_length=50)
#    horizontal_resolution = models.CharField(max_length=220)
#    horizontal_resolution_range = models.ForeignKey(HorizontalDataResolution)
#    vertical_resolution = models.CharField(max_length=220)
#    vertical_resolution_range = models.ForeignKey(VerticalDataResolution)
#    temporal_resolution = models.CharField(max_length=220)
#    temporal_resolution_range = models.ForeignKey(TemporalDataResolution)

class DatasetParameter(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)

    def __str__(self):
        return '%s:%s' %(self.dataset, self.parameter)

class DatasetURI(models.Model):

    uri = models.URLField(max_length=200, unique=True,
            validators=[URLValidator(schemes=URLValidator.schemes + ['file'])])
    dataset = models.ForeignKey(Dataset)

    objects = DatasetURIManager()

    def __str__(self):
        return '%s: %s'%(self.dataset, os.path.split(self.uri)[1])

    def protocol(self):
        return self.uri.split(':')[0]

    def save(self, *args, **kwargs):
        # Validation is not usually done in the models but rather via form
        # validation. We should discuss if we want it or not. Presently, we
        # check only that the uri is valid but we may also check if it exists
        # (although this isn't normally done either - see
        # https://docs.djangoproject.com/en/dev/internals/deprecation/ and
        # search "verify_exists")
        # Force field validation - but it fails although the uri is
        # (apparently) good... see the test..
        #self.full_clean()
        # Check that the uri exists?
        super(DatasetURI, self).save(*args, **kwargs)

class DatasetRelationship(models.Model):
    child = models.ForeignKey(Dataset, related_name='parents')
    parent = models.ForeignKey(Dataset, related_name='children')

