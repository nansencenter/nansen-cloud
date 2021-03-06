from django.db import models

from nansencloud.catalog.models import Dataset as CatalogDataset

from nansencloud.processing_ais.managers import DatasetManager

class Dataset(CatalogDataset):

    objects = DatasetManager()

    class Meta:
        proxy = True


