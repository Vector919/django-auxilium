from __future__ import unicode_literals, print_function
import inspect
from django.db import models
from django_auxilium.utils.functools import Decorator, cache


class FileFieldAutoDelete(Decorator):
    """
    Model decorator which automatically setups all the necessary signals to automatically
    remove files associated with given field when model instance is removed.

    Starting with Django 1.3 when model records are deleted via querysets (e.g.
    ``model.objects.filter(...).delete()``), the model's ``delete()`` method is no longer
    called. As a consequence, if the model has any file fields, those files will not
    be removed even if it is specified in the ``delete()`` method. The new way to remove
    files associated with a model is to use Django signals framework, or more specifically
    the ``post_delete`` signal. This decorator automatically connects the ``post_delete``
    signal which will remove the file associated with the specified file field.

    More about this can be found at Django 1.3 `release notes <http://bit.ly/UZypPb>`_.

    Parameters
    ----------
    field : str, unicode
        The file field
    signal_name_pattern : str, unicode, optional
        The name given to the signal function which will automatically remove the file.
        This can be a string formatted string. Into it, two parameters will be passed
        which are ``model`` and ``field``. ``model`` is a model class (not instance) to
        which the signal is being connected to and ``field`` is a name of the file field.
        The default pattern is ``post_delete_{model.__name__}_delete_{field}`` which
        results in patterns like *"post_delete_Model_delete_file_field"*. The reason
        why this pattern might be useful is because it can be used to disconnect the
        signal receiver at a later time.
    """
    PARAMETERS = ('field', 'signal_name_pattern')
    DEFAULTS = {'signal_name_pattern': 'post_delete_{model.__name__}_delete_{field}'}

    def get_wrapped_object(self):
        """
        Return the given model.

        Since signals are connected externally of a model class, the model class is not
        modified. All this method does is calls the ``validate_model()`` and
        ``connect_signal_function()`` class methods. Please refer to their documentation
        of what they do.

        See Also
        --------
        validate_model
        connect_signal_function
        """
        self.validate_model()
        self.connect_signal_function()

        return self.to_wrap

    def validate_model(self):
        """
        Validate the input to the decorator which is suppose to be a model.

        Make sure the given class is a subclass of Django's ``Model`` class. Also
        this method validates that the given field is present in the model and that it is
        a subclass of Django's ``FileField`` field class.

        Raises
        ------
        TypeError
            If the validation fails
        """
        if not inspect.isclass(self.to_wrap):
            raise TypeError('This decorator can only be applied to classes')
        if not issubclass(self.to_wrap, models.Model):
            raise TypeError('Decorator can only be applied to Django models')

        valid = True
        all_fields = self.to_wrap._meta.get_all_field_names()

        if self.parameters['field'] not in all_fields:
            valid = False

        if valid:
            field = self.to_wrap._meta.get_field_by_name(
                self.parameters['field'])[0].__class__
            if not issubclass(field, models.FileField):
                valid = False

        if not valid:
            m = 'Field "{}" must be a subclass of Django ``FileField``'
            raise TypeError(m.format(self.parameters['field']))

    def get_signal_name(self):
        """
        Using the ``signal_name_pattern`` pattern, return the formatted signal name.

        Returns
        -------
        name : str
            The name of the signal
        """
        return self.parameters['signal_name_pattern'].format(
            model=self.to_wrap,
            field=self.parameters['field']
        )

    @cache
    def get_signal_function(self):
        """
        Get the actual function which will be connected to the Django's signal which
        conforms to the ``post_delete`` signal signature::

            def receiver(sender, instance, *args, **kwargs): pass
        """
        def remove(sender, instance, *args, **kwargs):
            """
            Automatically remove the file field when model instance is deleted.
            """
            field = getattr(instance, self.parameters['field'], None)
            if field:
                method = getattr(field, 'delete', None)
                if method and callable(method):
                    method(save=False)

        return remove

    def connect_signal_function(self):
        """
        Connect the signal as returned by ``get_signal_function`` into the Django's
        signal's framework.
        """
        signal_name = self.get_signal_name()
        signal_function = self.get_signal_function()
        models.signals.post_delete.connect(signal_function,
                                           sender=self.to_wrap,
                                           weak=False,
                                           dispatch_uid=signal_name)


file_field_auto_delete = FileFieldAutoDelete.to_decorator()
