from geo.models import Point

from django.contrib.admin.filterspecs import FilterSpec, ChoicesFilterSpec
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

class CustomFilterSpec(ChoicesFilterSpec):

    my_lookup_kwarg = 'override_in_subclass'

    def prepare_choices(self):
        return []

    def title(self):
        # return the title displayed above your filter
        return "override in subclass"

    def __init__(self, f, request, params, model, model_admin):
        ChoicesFilterSpec.__init__(self, f, request, params, model, model_admin)
        self.lookup_kwarg = self.my_lookup_kwarg
        # get the current filter value from GET (we will use it to know
        # which filter item is selected)
        self.lookup_val = request.GET.get(self.lookup_kwarg)

        # Prepare the list of unique, country name, ordered alphabetically
        self.lookup_choices = self.prepare_choices()

    def choices(self, cl):
        # Generator that returns all the possible item in the filter
        # including an 'All' item.
        yield { 'selected': self.lookup_val is None,
                'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
                'display': _('All') }
        for val in self.lookup_choices:
            yield { 'selected' : smart_unicode(val) == self.lookup_val,
                    'query_string': cl.get_query_string({self.lookup_kwarg: val}),
                    'display': val }

def insert_filterspec(filterspec, field_attribute):
    # Here, we insert the new FilterSpec at the first position, to be sure
    # it gets picked up before any other
    FilterSpec.filter_specs.insert(
        0,
        # If the field has a `profilecountry_filter` attribute set to True
        # the this FilterSpec will be used
        (lambda f: getattr(f, field_attribute, False), filterspec))

class CountryFilterSpec(CustomFilterSpec):
    my_lookup_kwarg = "geom__country"

    def prepare_choices(self):
        return Point.objects.values_list(
            "country", flat=True).distinct().order_by("country")

    def title(self):
        return _("Country")

class StateFilterSpec(CustomFilterSpec):
    my_lookup_kwarg = "geom__state"

    def prepare_choices(self):
        return Point.objects.values_list(
            "state", flat=True).distinct().order_by("state")

    def title(self):
        return _("State")

class CityFilterSpec(CustomFilterSpec):
    my_lookup_kwarg = "geom__city"

    def prepare_choices(self):
        return Point.objects.values_list(
            "city", flat=True).distinct().order_by("city")

    def title(self):
        return _("City")

insert_filterspec(CountryFilterSpec, 'country_filter')
insert_filterspec(StateFilterSpec, 'state_filter')
insert_filterspec(CityFilterSpec, 'city_filter')

class UserCountryFilterSpec(CountryFilterSpec):
    my_lookup_kwarg = "profile__geom__country"
class UserStateFilterSpec(StateFilterSpec):
    my_lookup_kwarg = "profile__geom__state"
class UserCityFilterSpec(CityFilterSpec):
    my_lookup_kwarg = "profile__geom__city"

insert_filterspec(UserCountryFilterSpec, 'user_country_filter')
insert_filterspec(UserStateFilterSpec, 'user_state_filter')
insert_filterspec(UserCityFilterSpec, 'user_city_filter')
