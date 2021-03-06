
"""
This module exposes everything needed to generate a standard django form class
from a formidable object.

Given a formidable object, you can use :func:`get_dynamic_form_class` to get
its corresponding django form class.
"""
from collections import OrderedDict

from django import forms
from django.db.models import Prefetch

from formidable.forms import field_builder
from formidable.forms.conditions import conditions_register
from formidable.models import Access, Formidable, Item


class FormidableBoundFieldCache(dict):
    """
    In Django 1.8, bound fields are handled in the form context (__getitem__).
    However, we want to inject our own BoundField for FormatField in order to
    handle labels differently.
    This can be achieved by implementing the get_bound_field method in our
    field (available in Django >= 1.9). For now, if the method exists,
    the bound_field is switched-in at the form level.
    """
    def __setitem__(self, key, bf):
        form, field, name = bf.form, bf.field, bf.name
        if hasattr(field, 'get_bound_field'):
            bf = field.get_bound_field(form, name)
        return super().__setitem__(key, bf)


class BaseDynamicForm(forms.Form):
    """
    This class is used to generate the final Django form class corresponding to
    the formidable object.

    Please do not use this class directly, rather, you should check the
    endpoint :func:`get_dynamic_form_class`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bound_fields_cache = FormidableBoundFieldCache()

    def get_removed_fields(self, cleaned_data):
        """
        Build the list of fields to be removed due to conditional displays
        """
        # build a catalog of fields **targeted** by the conditions
        condition_targets = {}

        # For each condition, extract its status (should I display or not)
        for condition in self._conditions:
            # should we keep these fields?
            keep_fields = condition.keep_fields(cleaned_data)
            for field_id in condition.fields_ids:
                # Fill the catalog
                if field_id not in condition_targets:
                    condition_targets[field_id] = []
                condition_targets[field_id].append(keep_fields)
        # Here, the catalog contains fields targeted by 1 or many conditions.

        # If only one condition says "please display X", we'll keep X
        # That's why we gather the conditions using "any"
        condition_targets = {k: any(v) for k, v in condition_targets.items()}
        # We'll only remove fields that are targeted by conditions **and**
        # those conditions are false
        return (k for k, v in condition_targets.items() if not v)

    def clean(self):
        cleaned_data = super().clean()

        removed_fields = self.get_removed_fields(cleaned_data)
        for field_id in removed_fields:
            # Remove field from cleaned_data
            cleaned_data.pop(field_id, None)
            # Remove from eventual existing errors
            self.errors.pop(field_id, None)
            # The field might have been removed if it was a file field.
            if field_id in self.fields:
                del self.fields[field_id]

        return cleaned_data


def get_dynamic_form_class_from_schema(schema, field_factory=None):
    """
    Return a dynamically generated and contextualized form class

    """
    attrs = OrderedDict()
    field_factory = field_factory or field_builder.FormFieldFactory()
    doc = schema['description']
    for field in schema['fields']:
        try:
            form_field = field_factory.produce(field)
        except field_builder.SkipField:
            pass
        else:
            attrs[field['slug']] = form_field

    conditions = schema.get('conditions', None) or []
    attrs['_conditions'] = conditions_register.build(
        attrs,
        conditions
    )
    form_class = type(str('DynamicForm'), (BaseDynamicForm,), attrs)
    form_class.__doc__ = doc
    return form_class


def get_dynamic_form_class(formidable, role=None, field_factory=None):
    """
    This is the main method for getting a django form class from a formidable
    object.

    .. code-block:: python

        form_obj = Formidable.objects.get(pk=42)
        django_form_class = get_dynamic_form_class(form_obj)

    The optional :params:`role` argument provides a way to get the form class
    according to the access rights you specify by role. The :params:`role` must
    be a role id, as defined by the code pointed to in
    settings.FORMIDABLE_ACCESS_RIGHTS_LOADER.

    .. code-block:: python

        form_obj = Formidable.objects.get(pk=42)
        django_form_class = get_dynamic_form_class(form_obj, role='jedi')

    """

    attrs = OrderedDict()
    field_factory = field_factory or field_builder.FormFieldFactory()

    access_qs = Access.objects.all()
    if role:
        access_qs = access_qs.filter(access_id=role)

    fields = formidable.fields.prefetch_related(
        Prefetch('items', queryset=Item.objects.order_by('order')),
        Prefetch('accesses', queryset=access_qs),
        'validations', 'defaults'
    )

    for field in fields.order_by('order').all():
        try:
            form_field = field_factory.produce(field, role)
        except field_builder.SkipField:
            pass
        else:
            attrs[field.slug] = form_field

    conditions_json = formidable.conditions or []
    attrs['_conditions'] = conditions_register.build(attrs, conditions_json)
    return type(str('DynamicForm'), (BaseDynamicForm,), attrs)


class FormidableForm(forms.Form):
    """
    This is the main class available to build a formidable object with Django's
    form API syntax.

    It provides a class method :meth:`to_formidable` which saves the declared
    form as a formidable objects.

    Check the formidable.forms.fields module to see what fields are available
    when defining your form.
    """

    @classmethod
    def to_formidable(cls, label=None, description=None, instance=None):
        if not instance:
            if not label:
                raise ValueError("Label is required on creation mode")
            description = description or ''
            form = Formidable.objects.create(
                label=label, description=description
            )
        else:
            form = cls.get_clean_form(instance, label, description)

        order = 0
        for slug, field in cls.declared_fields.items():
            field.to_formidable(form, order, slug)
            order += 1

        return form

    @classmethod
    def get_clean_form(cls, form, label, description):
        """
        From a form definition and label and description value, the method
        clean all fields and validations attached to the form.
        If the label or description are not empty, those values are updated
        in the database *and* in memory.

        The returned object is a form without fields or validations , and
        new label and description if needed.
        """
        form.fields.all().delete()
        if description or label:
            kwargs = {
                'description': description or form.description,
                'label': label or form.label,
            }
            Formidable.objects.filter(pk=form.pk).update(**kwargs)
            form.label = kwargs['label']
            form.description = kwargs['description']

        return form
