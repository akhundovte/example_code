import time
import datetime
import asyncio
import logging

from typing import Dict
from collections import deque
from utils.timezone import now, localtime
from .utils import get_tasks, TaskType

OFFSET_FOR_EVERY = 2

logger = logging.getLogger('service')


class Scheduler:
    """
    Концепция:
        задачи сортируются по времени и записываются в очередь
        следующим шагом берем первую задачу из очереди и если время до выполнения отрицательное,
        то пропускаем выполнение только если это происходит при старте,
        т.к. надо перебрать задачи который уже сегодня не надо выполнять

        после того, как очередь закончилась (это значит сегодняшние задачи перебрали),
        опять записываем в очередь отсортированные задачи,
        только теперь, если время отрицательное прибавляем 1 день (т.е. на следующий день переносим)
        и ждем выполнения этой задачи
    """
    def __init__(self,
                 schedule: Dict[str, Dict[str, int]],
                 loop=None) -> None:
        """ """
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self.tasks = self.get_periodic_sorted_tasks(schedule)
        self.queue = deque(self.tasks)
        self.handle = None

    def get_periodic_sorted_tasks(self, schedule):
        dt_now = localtime(now())
        tasks = get_tasks(schedule)

        tasks_periodic = []
        count_every = 0
        for task in tasks:
            type_task = task.type
            if type_task == 'every':
                time_task = task.time
                offset_minutes = count_every + OFFSET_FOR_EVERY
                dt_task = dt_now + datetime.timedelta(minutes=offset_minutes)
                dt_limit = dt_task + datetime.timedelta(days=1)
                while dt_task < dt_limit:
                    struct_time = dt_task.timetuple()
                    time = {
                        'hour': struct_time.tm_hour, 'minute': struct_time.tm_min,
                        'second': struct_time.tm_sec, 'microsecond': 0,
                        }
                    tasks_periodic.append(TaskType(task.name, 'periodic', task.executor, time))
                    time_task_kw = {
                        'hours': time_task.get('hour', 0),
                        'minutes': time_task.get('minute', 0),
                        'seconds': time_task.get('second', 0),
                        }
                    dt_task = dt_task + datetime.timedelta(**time_task_kw)
                count_every += 1
            else:
                tasks_periodic.append(task)

        return sorted(tasks_periodic, key=lambda item: dt_now.replace(**item.time))

    def start(self):
        job, wait_seconds = self.get_next(call_in_start=True)
        self.handle = self.loop.call_later(wait_seconds, self.wakeup, job)

    def stop(self):
        """
        """
        if self.handle is not None:
            self.handle.cancel()
        self.handle = None

    def wakeup(self, job):
        """
        """
        # asyncio.gather(job())
        asyncio.create_task(job())
        logger.info(f"create_task {str(job)}")
        next_job, next_wait_seconds = self.get_next()
        logger.info(f"next_job {str(next_job)} - later {next_wait_seconds}")
        self.handle = self.loop.call_later(next_wait_seconds, self.wakeup, next_job)

    def get_next(self, call_in_start=False):
        while True:
            try:
                next_item = self.queue.popleft()
                wait_seconds = self.get_wait_seconds(next_item.time)
                if wait_seconds < 0 and call_in_start:
                    continue
                break
            except IndexError:  # очередь закончилась
                self.queue = deque(self.tasks)
                next_item = self.queue.popleft()
                wait_seconds = self.get_wait_seconds(next_item.time)
                if wait_seconds < 0:
                    dt_reference = localtime(now()) + datetime.timedelta(days=1)
                    wait_seconds = self.get_wait_seconds(next_item.time, dt_reference)
                break
        return next_item.executor, wait_seconds

    def get_wait_seconds(self, time_struct, dt_reference=None):
        if dt_reference is None:
            dt_reference = localtime(now())
        dt = dt_reference.replace(**time_struct)
        wait_seconds = int(dt.timestamp()) - int(time.time())
        return wait_seconds
