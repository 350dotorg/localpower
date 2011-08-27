from django.db import models
from django.contrib.admin.filterspecs import FilterSpec, ChoicesFilterSpec,DateFieldFilterSpec
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from datetime import date

class HasHappenedFilterSpec(DateFieldFilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(HasHappenedFilterSpec, self).__init__(f, request, params, model,
                                                   model_admin)
        today = date.today()
        self.links = (
            (_('Any'), {}),
            (_('Yes'), {'%s__lt' % self.field.name: str(today),
                       }),
            (_('No'), {'%s__gte' % self.field.name: str(today),
                    }),
        )

    def title(self):
        return _("Has Happened")

FilterSpec.filter_specs.insert(0, (lambda f: getattr(f, 'has_happened', False),
                                   HasHappenedFilterSpec))
