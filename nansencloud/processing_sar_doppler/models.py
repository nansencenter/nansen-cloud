from django.db import models

from nansencloud.catalog.models import Dataset as CatalogDataset
from nansencloud.processing_sar_doppler.managers import DatasetManager

class Dataset(CatalogDataset):

    objects = DatasetManager()

    class Meta:
        proxy = True

