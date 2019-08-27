# Airflow Custom Logger Example
You can customize pretty much everything about airflow logging.

- [Background](#background)
- [The Implementation](#the-implementation)
- [How To](#how-to)
- [Issues I Ran Into](#issues-i-ran-into)

---

### Background
My company uses Datadog for logging and monitoring performance metrics for our services. We use kubernetes and needed a way to surface airflow task runs to datadog.

1. My first implementation was to have datadog tail the airflow log directory. Unfortunately, this would eventually lead to a scaling issue as airflow logs per dag/task/run_date/job. Datadog would struggle to handle the load.

2. Second implementation was to piggy back off of airflow's new elasticsearch log implementation in version 1.10.4. I was quite fortunate to stumble upon this only about 2 weeks after it's release. The community had added functionality to the elasticsearch logger which printed to STDOUT. It uses Pythons standard logging library, and is build with StreamHandler. This would log in serial. This was good because, datadog by default reads from STDOUT and STDERR. I just took the elasticsearch logger and made sure that it wrote to the default file as well. There was an issue with this... When writing to file, it would duplicate the logs. In stdout, there wasn't an issue.

3. This is the example implmentation. Decided that the line by line logs were not very useful in Datadog UI. I took the elasticsearch logger and stripped it bare. Now, it writes to the default file, and once it finishes writing to file, it'll read the file into a string and write the contents to stdout. Worked perfectly for our use case. Nonetheless, the airflow documentation doesn't make it very clear how much you can customize the logger. It seems that you can customize it as much as you want! You just need to edit `config.handlers.task.class` to reference the correct custom module.

### The Implementation
- The reason why we are extending file_task_hander with is described in the issues below. This handler just wraps the file_task_handler with a stream_handler, waits until the file_task_handler closes, reads the log file into a string, and then prints to stdout. Then datadog will pick it up from stdout. The implmentation is used in kubernetes pods with a datadog-agent daemonset.

### How To
```
docker-compose build
docker-compose up
```

### Issues I ran into
- I tried setting `propagate=true` in `config.loggers.airflow.task`, but ran into an issue where the kubernetes pods were eating up all the CPU and dying. After some testing, it seems that even if you just extend the File_task_handler, and try to `print('hello')`, it still has some sort of memory leak. Didn't really investigate into this, but could be from either the python standard library, or the logger implmentation... I chose to not waste time investigating into this.