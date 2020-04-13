

from pony import orm
import sys


def override_entity_wrapper(for_type, instance_type):
  """
  Sets an entity wrapper for the Pony ORM Entity class that is defined
  in the scope where this function is called.

  Currently only supports overriding the class that is used when resolving
  an #orm.Set attribute (which is a subclass of #orm.core.SetInstance), by
  overriding `_get_set_wrapper_subclass_()`.
  """

  if for_type is orm.Set:
    assert issubclass(instance_type, orm.core.SetInstance)

    @classmethod
    def _get_set_wrapper_subclass_(entity):
      result_cls = entity._set_wrapper_subclass_
      if result_cls is None:
        mixin = entity._get_propagation_mixin_()
        cls_name = entity.__name__ + 'Set'
        result_cls = type(cls_name, (instance_type, mixin), {})
        entity._set_wrapper_subclass_ = result_cls
      return result_cls

    sys._getframe(1).f_locals['_get_set_wrapper_subclass_'] = _get_set_wrapper_subclass_
  else:
    raise TypeError('unsupported for_type: {!r}'.format(for_type))
