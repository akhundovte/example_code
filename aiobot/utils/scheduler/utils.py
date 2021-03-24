import collections

from importlib import import_module

TaskType = collections.namedtuple('TaskType', ['name', 'type', 'executor', 'time'])

# по аналогии get_callable из django\urls\utils.py


def get_tasks(schedule):
    tasks = []
    for name, task_data in schedule.items():
        path_executor = task_data['path']
        mod_name, func_name = get_mod_func(path_executor)
        if not func_name:  # No '.' in lookup_view
            raise ImportError("Could not import '%s'. The path must be fully qualified." % path_executor)
        try:
            mod = import_module(mod_name)
        except ImportError:
            raise
        else:
            try:
                task_func = getattr(mod, func_name)
            except AttributeError:
                raise ImportError(
                    "Could not import '%s'. View does not exist in module %s." %
                    (path_executor, mod_name)
                    )
        tasks.append(TaskType(name, task_data['type'], task_func, task_data['time']))
    return tasks


def get_mod_func(callback):
    # Convert 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]
