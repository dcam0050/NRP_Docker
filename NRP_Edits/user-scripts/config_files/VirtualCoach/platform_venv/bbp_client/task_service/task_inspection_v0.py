'''utilities to extract information from a local task'''

from task_types import TaskOps as to

import logging

L = logging.getLogger(__name__)


def get_properties(_, module_src):
    '''Obtain properties for a new task registration'''

    # sensible defaults:
    props = {
        'state': 'default',
        'compatible_queues': ['all']
    }

    props.update(parse_properties_from_source(module_src))

    return props


def parse_properties_from_source(module_str):  # pylint: disable=R0912
    '''we need to find the task parameters, such that we can
    serve a them for the gui generation.  However, we don't want to load
    the module, because we can't trust the code.  So we parse the AST
    instead

    From: http://stackoverflow.com/a/9580006
    '''
    import ast

    props = {
        'accepts': [],
        'returns': []
    }

    def visit_FunctionDef(node):
        '''visitor to function definitions, needed to extract decorator'''
        for e in node.decorator_list:
            assert isinstance(e, (ast.Call, ast.Name))

            decorator_name = None

            if isinstance(e, ast.Call):  # @task(args, ...)
                decorator_name = e.func.id

                for k in e.keywords:
                    if k.arg in ('accepts', 'returns'):
                        types = to.convert_to_types(to.parse_val(k.value))
                        types_list = to.make_iterable(types)
                        if isinstance(types_list, tuple):
                            types_list = list(types_list)

                        props[k.arg] = types_list

                    else:
                        raise KeyError('decorator has unknown argument')

            elif isinstance(e, ast.Name):  # @task [ie: naked]
                decorator_name = e.id

            if 'task' == decorator_name:
                visit_FunctionDef.task_count += 1

                visit_FunctionDef.function_name = node.name

                visit_FunctionDef.function_params = [to.parse_val(arg)
                                                     for arg in node.args.args]
            else:
                continue

    visit_FunctionDef.function_name = None
    visit_FunctionDef.function_params = []
    visit_FunctionDef.task_count = 0  # number of decorators named task

    # extract inline meta properties
    inline_properties = dict(_task_full_name='full_name',
                             _task_caption='caption',
                             _task_description='description',
                             _task_author='author',
                             _task_categories='categories',
                             _task_compatible_queues='compatible_queues')

    def visit_Assign(node):
        '''visitor to assigns, needed for inline properties'''
        if not hasattr(node.targets[0], 'id'):
            return

        if 1 == len(node.targets) and node.targets[0].id in inline_properties:
            value = to.parse_val(node.value)
            attr_name = inline_properties.pop(node.targets[0].id)
            props[attr_name] = value

    visitor = ast.NodeVisitor()
    visitor.visit_FunctionDef = visit_FunctionDef
    visitor.visit_Assign = visit_Assign
    visitor.visit(compile(module_str, '?', 'exec', ast.PyCF_ONLY_AST))

    if 0 == visit_FunctionDef.task_count:
        raise ValueError('Task has no @task decorator')

    elif 1 < visit_FunctionDef.task_count:
        raise ValueError('Task has too many @task decorators')

    props['task_name'] = visit_FunctionDef.function_name

    # organize types in the accepts list to be the same as the function
    props['accepts'] = to.order_args(visit_FunctionDef.function_params, props['accepts'])

    props['accepts'] = \
        [{'name': param_name, 'type': type_def}
         for param_name, type_def
         in zip(visit_FunctionDef.function_params, props['accepts'])]

    # this could be easily extracted from the decorator or docstring
    # but for the time being, let's just auto generate them
    func_rets = ['return_%d' % i for i in range(len(props['returns']))]
    props['returns'] = [{'name': ret_name, 'type': type_def}
                        for ret_name, type_def
                        in zip(func_rets, props['returns'])]

    return props
