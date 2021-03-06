from __future__ import unicode_literals

import functools
import sys
import tablib
import traceback
from copy import deepcopy

from diff_match_patch import diff_match_patch

from django import VERSION
from django.conf import settings
from django.core.management.color import no_style
from django.db import connections, transaction, DEFAULT_DB_ALIAS
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query import QuerySet
from django.db.transaction import TransactionManagementError
from django.utils import six
from django.utils.safestring import mark_safe

from . import widgets
from .fields import Field
from .instance_loaders import ModelInstanceLoader
from .results import Error, Result, RowResult

try:
    from django.db.transaction import atomic, savepoint, savepoint_rollback, savepoint_commit  # noqa
except ImportError:
    from .django_compat import atomic, savepoint, savepoint_rollback, savepoint_commit  # noqa


if VERSION < (1, 8):
    from django.db.models.related import RelatedObject
    ForeignObjectRel = RelatedObject
else:
    from django.contrib.postgres.fields import ArrayField
    from django.db.models.fields.related import ForeignObjectRel
    RelatedObject = None

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

# Set default logging handler to avoid "No handler found" warnings.
import logging  # isort:skip
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

USE_TRANSACTIONS = getattr(settings, 'IMPORT_EXPORT_USE_TRANSACTIONS', False)


class ResourceOptions(object):
    """
    The inner Meta class allows for class-level configuration of how the
    Resource should behave. The following options are available:
    """

    model = None
    """
    Django Model class. It is used to introspect available
    fields.

    """
    fields = None
    """
    Controls what introspected fields the Resource should include. A whitelist
    of fields.
    """

    exclude = None
    """
    Controls what introspected fields the Resource should
    NOT include. A blacklist of fields.
    """

    instance_loader_class = None
    """
    Controls which class instance will take
    care of loading existing objects.
    """

    import_id_fields = ['id']
    """
    Controls which object fields will be used to
    identify existing instances.
    """

    export_order = None
    """
    Controls export order for columns.
    """

    widgets = None
    """
    This dictionary defines widget kwargs for fields.
    """

    use_transactions = None
    """
    Controls if import should use database transactions. Default value is
    ``None`` meaning ``settings.IMPORT_EXPORT_USE_TRANSACTIONS`` will be
    evaluated.
    """

    skip_unchanged = False
    """
    Controls if the import should skip unchanged records. Default value is
    False
    """

    report_skipped = True
    """
    Controls if the result reports skipped rows Default value is True
    """


class DeclarativeMetaclass(type):

    def __new__(cls, name, bases, attrs):
        declared_fields = []
        meta = ResourceOptions()

        # If this class is subclassing another Resource, add that Resource's
        # fields. Note that we loop over the bases in *reverse*. This is
        # necessary in order to preserve the correct order of fields.
        for base in bases[::-1]:
            if hasattr(base, 'fields'):
                declared_fields = list(six.iteritems(base.fields)) + declared_fields
                # Collect the Meta options
                options = getattr(base, 'Meta', None)
                for option in [option for option in dir(options)
                               if not option.startswith('_')]:
                    setattr(meta, option, getattr(options, option))

        # Add direct fields
        for field_name, obj in attrs.copy().items():
            if isinstance(obj, Field):
                field = attrs.pop(field_name)
                if not field.column_name:
                    field.column_name = field_name
                declared_fields.append((field_name, field))

        attrs['fields'] = OrderedDict(declared_fields)
        new_class = super(DeclarativeMetaclass, cls).__new__(cls, name,
                                                             bases, attrs)

        # Add direct options
        options = getattr(new_class, 'Meta', None)
        for option in [option for option in dir(options)
                       if not option.startswith('_')]:
            setattr(meta, option, getattr(options, option))
        new_class._meta = meta

        return new_class


class Resource(six.with_metaclass(DeclarativeMetaclass)):
    """
    Resource defines how objects are mapped to their import and export
    representations and handle importing and exporting data.
    """

    @classmethod
    def get_result_class(self):
        """
        Returns the class used to store the result of an import.
        """
        return Result

    @classmethod
    def get_row_result_class(self):
        """
        Returns the class used to store the result of a row import.
        """
        return RowResult

    @classmethod
    def get_error_result_class(self):
        """
        Returns the class used to store an error resulting from an import.
        """
        return Error

    def get_use_transactions(self):
        if self._meta.use_transactions is None:
            return USE_TRANSACTIONS
        else:
            return self._meta.use_transactions

    def get_fields(self):
        """
        Returns fields sorted according to
        :attr:`~import_export.resources.ResourceOptions.export_order`.
        """
        return [self.fields[f] for f in self.get_export_order()]

    @classmethod
    def get_field_name(cls, field):
        """
        Returns the field name for a given field.
        """
        for field_name, f in cls.fields.items():
            if f == field:
                return field_name
        raise AttributeError("Field %s does not exists in %s resource" % (
            field, cls))

    def init_instance(self, row=None):
        raise NotImplementedError()

    def get_instance(self, instance_loader, row):
        """
        Calls the :doc:`InstanceLoader <api_instance_loaders>`.
        """
        return instance_loader.get_instance(row)

    def get_or_init_instance(self, instance_loader, row):
        """
        Either fetches an already existing instance or initializes a new one.
        """
        instance = self.get_instance(instance_loader, row)
        if instance:
            return (instance, False)
        else:
            return (self.init_instance(row), True)

    def save_instance(self, instance, dry_run=False):
        """
        Takes care of saving the object to the database.

        Keep in mind that this is done by calling ``instance.save()``, so
        objects are not created in bulk!
        """
        self.before_save_instance(instance, dry_run)
        if not dry_run:
            instance.save()
        self.after_save_instance(instance, dry_run)

    def before_save_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_save_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def delete_instance(self, instance, dry_run=False):
        """
        Calls :meth:`instance.delete` as long as ``dry_run`` is not set.
        """
        self.before_delete_instance(instance, dry_run)
        if not dry_run:
            instance.delete()
        self.after_delete_instance(instance, dry_run)

    def before_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def after_delete_instance(self, instance, dry_run):
        """
        Override to add additional logic. Does nothing by default.
        """
        pass

    def import_field(self, field, obj, data):
        """
        Calls :meth:`import_export.fields.Field.save` if ``Field.attribute``
        and ``Field.column_name`` are found in ``data``.
        """
        if field.attribute and field.column_name in data:
            field.save(obj, data)

    def import_obj(self, obj, data, dry_run):
        """
        Traverses every field in this Resource and calls
        :meth:`~import_export.resources.Resource.import_field`.
        """
        for field in self.get_fields():
            if isinstance(field.widget, widgets.ManyToManyWidget):
                continue
            self.import_field(field, obj, data)

    def save_m2m(self, obj, data, dry_run):
        """
        Saves m2m fields.

        Model instance need to have a primary key value before
        a many-to-many relationship can be used.
        """
        if not dry_run:
            for field in self.get_fields():
                if not isinstance(field.widget, widgets.ManyToManyWidget):
                    continue
                self.import_field(field, obj, data)

    def for_delete(self, row, instance):
        """
        Returns ``True`` if ``row`` importing should delete instance.

        Default implementation returns ``False``.
        Override this method to handle deletion.
        """
        return False

    def skip_row(self, instance, original):
        """
        Returns ``True`` if ``row`` importing should be skipped.

        Default implementation returns ``False`` unless skip_unchanged == True.
        Override this method to handle skipping rows meeting certain
        conditions.
        """
        if not self._meta.skip_unchanged:
            return False
        for field in self.get_fields():
            try:
                # For fields that are models.fields.related.ManyRelatedManager
                # we need to compare the results
                if list(field.get_value(instance).all()) != list(field.get_value(original).all()):
                    return False
            except AttributeError:
                if field.get_value(instance) != field.get_value(original):
                    return False
        return True

    def get_diff(self, original, current, dry_run=False):
        """
        Get diff between original and current object when ``import_data``
        is run.

        ``dry_run`` allows handling special cases when object is not saved
        to database (ie. m2m relationships).
        """
        data = []
        dmp = diff_match_patch()
        for field in self.get_fields():
            v1 = self.export_field(field, original) if original else ""
            v2 = self.export_field(field, current) if current else ""
            diff = dmp.diff_main(force_text(v1), force_text(v2))
            dmp.diff_cleanupSemantic(diff)
            html = dmp.diff_prettyHtml(diff)
            html = mark_safe(html)
            data.append(html)
        return data

    def get_diff_headers(self):
        """
        Diff representation headers.
        """
        return self.get_export_headers()

    def before_import(self, dataset, dry_run, **kwargs):
        """
        Override to add additional logic. Does nothing by default.

        This method receives the ``dataset`` that's going to be imported, the
        ``dry_run`` parameter which determines whether changes are saved to
        the database, and any additional keyword arguments passed to
        ``import_data`` in a ``kwargs`` dict.
        """
        return dataset

    def after_import(self, dataset, result, dry_run, **kwargs):
        """
        Override to add additional logic. Does nothing by default.

        This method receives the ``dataset`` that's just been imported, the
        ``result`` of the import and the ``dry_run`` parameter which determines
        whether changes will be saved to the database, and any additional
        keyword arguments passed to ``import_data`` in a ``kwargs`` dict. This
        method runs after the main import finishes but before the changes are
        committed or rolled back.
        """
        pass

    def import_row(self, row, instance_loader, dry_run=False, **kwargs):
        """
        Imports data from ``tablib.Dataset``. Refer to :doc:`import_workflow`
        for a more complete description of the whole import process.

        :param row: A ``dict`` of the row to import

        :param instance_loader: The instance loader to be used to load the row

        :param dry_run: If ``dry_run`` is set, or error occurs, transaction
            will be rolled back.
        """
        try:
            row_result = self.get_row_result_class()()
            instance, new = self.get_or_init_instance(instance_loader, row)
            if new:
                row_result.import_type = RowResult.IMPORT_TYPE_NEW
            else:
                row_result.import_type = RowResult.IMPORT_TYPE_UPDATE
            row_result.new_record = new
            row_result.object_repr = force_text(instance)
            row_result.object_id = instance.pk
            original = deepcopy(instance)
            if self.for_delete(row, instance):
                if new:
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                    row_result.diff = self.get_diff(None, None, dry_run)
                else:
                    row_result.import_type = RowResult.IMPORT_TYPE_DELETE
                    self.delete_instance(instance, dry_run)
                    row_result.diff = self.get_diff(original, None, dry_run)
            else:
                self.import_obj(instance, row, dry_run)
                if self.skip_row(instance, original):
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                else:
                    with transaction.atomic():
                        self.save_instance(instance, dry_run)
                    self.save_m2m(instance, row, dry_run)
                    # Add object info to RowResult for LogEntry
                    row_result.object_repr = force_text(instance)
                    row_result.object_id = instance.pk
                row_result.diff = self.get_diff(original, instance, dry_run)
        except Exception as e:
            # There is no point logging a transaction error for each row
            # when only the original error is likely to be relevant
            if not isinstance(e, TransactionManagementError):
                logging.exception(e)
            tb_info = traceback.format_exc()
            row_result.errors.append(self.get_error_result_class()(e, tb_info, row))
        return row_result

    @atomic()
    def import_data(self, dataset, dry_run=False, raise_errors=False,
                    use_transactions=None, **kwargs):
        """
        Imports data from ``tablib.Dataset``. Refer to :doc:`import_workflow`
        for a more complete description of the whole import process.

        :param dataset: A ``tablib.Dataset``

        :param raise_errors: Whether errors should be printed to the end user
            or raised regularly.

        :param use_transactions: If ``True`` import process will be processed
            inside transaction.

        :param dry_run: If ``dry_run`` is set, or error occurs, transaction
            will be rolled back.
        """
        result = self.get_result_class()()
        result.diff_headers = self.get_diff_headers()
        result.totals = OrderedDict([(RowResult.IMPORT_TYPE_NEW, 0),
                                     (RowResult.IMPORT_TYPE_UPDATE, 0),
                                     (RowResult.IMPORT_TYPE_DELETE, 0),
                                     (RowResult.IMPORT_TYPE_SKIP, 0),
                                     (RowResult.IMPORT_TYPE_ERROR, 0),
                                     ('total', len(dataset))])

        if use_transactions is None:
            use_transactions = self.get_use_transactions()

        if use_transactions is True:
            # when transactions are used we want to create/update/delete object
            # as transaction will be rolled back if dry_run is set
            real_dry_run = False
            sp1 = savepoint()
        else:
            real_dry_run = dry_run

        try:
            dataset = self.before_import(dataset, real_dry_run, **kwargs)
        except Exception as e:
            logging.exception(e)
            tb_info = traceback.format_exc()
            result.base_errors.append(self.get_error_result_class()(e, tb_info))
            if raise_errors:
                if use_transactions:
                    savepoint_rollback(sp1)
                raise

        instance_loader = self._meta.instance_loader_class(self, dataset)

        # Update the total in case the dataset was altered by before_import()
        result.totals['total'] = len(dataset)

        for row in dataset.dict:
            row_result = self.import_row(row, instance_loader, real_dry_run, **kwargs)
            if row_result.errors:
                result.totals[row_result.IMPORT_TYPE_ERROR] += 1
                if raise_errors:
                    if use_transactions:
                        savepoint_rollback(sp1)
                    raise row_result.errors[-1].error
            else:
                result.totals[row_result.import_type] += 1
            if (row_result.import_type != RowResult.IMPORT_TYPE_SKIP or
                    self._meta.report_skipped):
                result.rows.append(row_result)

        try:
            self.after_import(dataset, result, real_dry_run, **kwargs)
        except Exception as e:
            logging.exception(e)
            tb_info = traceback.format_exc()
            result.base_errors.append(self.get_error_result_class()(e, tb_info))
            if raise_errors:
                if use_transactions:
                    savepoint_rollback(sp1)
                raise

        if use_transactions:
            if dry_run or result.has_errors():
                savepoint_rollback(sp1)
            else:
                savepoint_commit(sp1)

        return result

    def get_export_order(self):
        order = tuple(self._meta.export_order or ())
        return order + tuple(k for k in self.fields.keys() if k not in order)

    def export_field(self, field, obj):
        field_name = self.get_field_name(field)
        method = getattr(self, 'dehydrate_%s' % field_name, None)
        if method is not None:
            return method(obj)
        return field.export(obj)

    def export_resource(self, obj):
        return [self.export_field(field, obj) for field in self.get_fields()]

    def get_export_headers(self):
        headers = [
            force_text(field.column_name) for field in self.get_fields()]
        return headers
        
    def get_user_visible_fields(self):
        return self.get_fields()

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)

        if isinstance(queryset, QuerySet):
            # Iterate without the queryset cache, to avoid wasting memory when
            # exporting large datasets.
            iterable = queryset.iterator()
        else:
            iterable = queryset
        for obj in iterable:
            data.append(self.export_resource(obj))
        return data


class ModelDeclarativeMetaclass(DeclarativeMetaclass):

    def __new__(cls, name, bases, attrs):
        new_class = super(ModelDeclarativeMetaclass,
                          cls).__new__(cls, name, bases, attrs)

        opts = new_class._meta

        if not opts.instance_loader_class:
            opts.instance_loader_class = ModelInstanceLoader

        if opts.model:
            model_opts = opts.model._meta
            declared_fields = new_class.fields

            field_list = []
            for f in sorted(model_opts.fields + model_opts.many_to_many):
                if opts.fields is not None and not f.name in opts.fields:
                    continue
                if opts.exclude and f.name in opts.exclude:
                    continue
                if f.name in declared_fields:
                    continue

                field = new_class.field_from_django_field(f.name, f,
                                                          readonly=False)
                field_list.append((f.name, field, ))

            new_class.fields.update(OrderedDict(field_list))

            # add fields that follow relationships
            if opts.fields is not None:
                field_list = []
                for field_name in opts.fields:
                    if field_name in declared_fields:
                        continue
                    if field_name.find('__') == -1:
                        continue

                    model = opts.model
                    attrs = field_name.split('__')
                    for i, attr in enumerate(attrs):
                        verbose_path = ".".join([opts.model.__name__] + attrs[0:i+1])

                        try:
                            if VERSION >= (1, 8):
                                f = model._meta.get_field(attr)
                            else:
                                f = model._meta.get_field_by_name(attr)[0]
                        except FieldDoesNotExist as e:
                            logging.exception(e)
                            raise FieldDoesNotExist(
                                "%s: %s has no field named '%s'" %
                                (verbose_path, model.__name__, attr))

                        if i < len(attrs) - 1:
                            # We're not at the last attribute yet, so check
                            # that we're looking at a relation, and move on to
                            # the next model.
                            if isinstance(f, ForeignObjectRel):
                                if RelatedObject is None:
                                    model = f.related_model
                                else:
                                    # Django < 1.8
                                    model = f.model
                            else:
                                if f.rel is None:
                                    raise KeyError(
                                        '%s is not a relation' % verbose_path)
                                model = f.rel.to

                    if isinstance(f, ForeignObjectRel):
                        f = f.field

                    field = new_class.field_from_django_field(field_name, f,
                                                              readonly=True)
                    field_list.append((field_name, field))

                new_class.fields.update(OrderedDict(field_list))

        return new_class


class ModelResource(six.with_metaclass(ModelDeclarativeMetaclass, Resource)):
    """
    ModelResource is Resource subclass for handling Django models.
    """

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        """
        Returns the widget that would likely be associated with each
        Django type.
        """
        result = default
        internal_type = f.get_internal_type()
        if internal_type in ('ManyToManyField', ):
            result = functools.partial(widgets.ManyToManyWidget,
                                       model=f.rel.to)
        if internal_type in ('ForeignKey', 'OneToOneField', ):
            result = functools.partial(widgets.ForeignKeyWidget,
                                       model=f.rel.to)
        if internal_type in ('DecimalField', ):
            result = widgets.DecimalWidget
        if internal_type in ('DateTimeField', ):
            result = widgets.DateTimeWidget
        elif internal_type in ('DateField', ):
            result = widgets.DateWidget
        elif internal_type in ('TimeField', ):
            result = widgets.TimeWidget
        elif internal_type in ('FloatField',):
            result = widgets.FloatWidget
        elif internal_type in ('IntegerField', 'PositiveIntegerField',
                               'BigIntegerField', 'PositiveSmallIntegerField',
                               'SmallIntegerField', 'AutoField'):
            result = widgets.IntegerWidget
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            result = widgets.BooleanWidget
        elif VERSION >= (1, 8):
            if type(f) == ArrayField:
                return widgets.SimpleArrayWidget
        return result

    @classmethod
    def widget_kwargs_for_field(self, field_name):
        """
        Returns widget kwargs for given field_name.
        """
        if self._meta.widgets:
            return self._meta.widgets.get(field_name, {})
        return {}

    @classmethod
    def field_from_django_field(self, field_name, django_field, readonly):
        """
        Returns a Resource Field instance for the given Django model field.
        """

        FieldWidget = self.widget_from_django_field(django_field)
        widget_kwargs = self.widget_kwargs_for_field(field_name)
        field = Field(
            attribute=field_name,
            column_name=field_name,
            widget=FieldWidget(**widget_kwargs),
            readonly=readonly,
            default=django_field.default,
        )
        return field

    def get_import_id_fields(self):
        """
        """
        return self._meta.import_id_fields

    def get_queryset(self):
        """
        Returns a queryset of all objects for this model. Override this if you
        want to limit the returned queryset.
        """
        return self._meta.model.objects.all()

    def init_instance(self, row=None):
        """
        Initializes a new Django model.
        """
        return self._meta.model()

    def after_import(self, dataset, result, dry_run, **kwargs):
        """
        Reset the SQL sequences after new objects are imported
        """
        # Adapted from django's loaddata
        if not dry_run and any(r.import_type == RowResult.IMPORT_TYPE_NEW for r in result.rows):
            connection = connections[DEFAULT_DB_ALIAS]
            sequence_sql = connection.ops.sequence_reset_sql(no_style(), [self._meta.model])
            if sequence_sql:
                cursor = connection.cursor()
                try:
                    for line in sequence_sql:
                        cursor.execute(line)
                finally:
                    cursor.close()


def modelresource_factory(model, resource_class=ModelResource):
    """
    Factory for creating ``ModelResource`` class for given Django model.
    """
    attrs = {'model': model}
    Meta = type(str('Meta'), (object,), attrs)

    class_name = model.__name__ + str('Resource')

    class_attrs = {
        'Meta': Meta,
    }

    metaclass = ModelDeclarativeMetaclass
    return metaclass(class_name, (resource_class,), class_attrs)
