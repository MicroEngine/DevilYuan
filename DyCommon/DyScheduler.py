import threading
import time
from datetime import datetime
from collections import namedtuple


class DyScheduler:
    """
        任务调度器
        由于APScheduler可能会发生Job missed的情况，所以自己写一个。
        !!!不支持一天开始和结束的几分钟。
    """
    Job = namedtuple('Job', 'job dayOfWeek timeOfDay')
    precision = 60*2 # 2 minutes


    def __init__(self):
        self._jobs = []

        self._active = False
        self._hand = None
        self._preTime = None

    def addJob(self, job, dayOfWeek, timeOfDay):
        """
            @job: job的处理函数
            @dayOfWeek: set, like {1, 2, 3, 4, 5, 6, 7}
            @timeOfDay: string, like '18:31:00'
        """
        self._jobs.append(self.Job(job, dayOfWeek, timeOfDay))

    def _run(self):
        while self._active:
            now = datetime.now()
            dayOfWeek = now.weekday() + 1
            curTime = now.strftime('%H:%M:%S')

            if self._preTime is not None:
                for job in self._jobs:
                    if dayOfWeek in job.dayOfWeek and self._preTime <= job.timeOfDay < curTime:
                        job.job()

            self._preTime = curTime

            time.sleep(self.precision)

    def start(self):
        self._active = True

        self._hand = threading.Thread(target=self._run)
        self._hand.start()

    def shutdown(self):
        self._active = False

        self._hand.join()

        self._hand = None
        self._preTime = None