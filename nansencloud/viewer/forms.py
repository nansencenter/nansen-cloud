from django.contrib.gis import forms
from django.utils import timezone

from nansencloud.viewer.models import Search

from leaflet.forms.widgets import LeafletWidget


class SearchForm(forms.ModelForm):

    class Meta:
        #model = TestSearch
        #fields = ['date0', 'date1', 'source']
        model = Search
        fields = ['polygon', 'date0', 'date1', 'source']
        labels = {'polygon':''}
        widgets = {'polygon': LeafletWidget(),
                   'date0': forms.DateInput(attrs={'class':'datepicker'}),
                   'date1': forms.DateInput(attrs={'class':'datepicker'}),}

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop('initial', {})
        initial['date0'] = timezone.datetime(2000, 1, 1,
                    tzinfo=timezone.utc).date(),
        initial['date1'] = timezone.now().date()
        super(SearchForm, self).__init__(initial=initial, *args, **kwargs)
