# 改善 Celery 分散式任務日誌的追蹤性

這篇紀錄旨在探討如何提升 Celery 日誌的可追蹤性和閱讀性，讓管理和調試過程更為高效。

## 1. 識別日誌追蹤的挑戰

在面對原始的 Celery 日誌時，我們遇到了幾個主要的挑戰：

- **任務追蹤困難**：從大量日誌中快速識別特定任務的日誌變得困難。
- **缺乏清晰的上下文連結**：日誌條目間的關聯不夠明確，追蹤不同任務之間的依賴和觸發變得相當頭痛。
- **日誌冗長**：大量重複的信息和缺乏重點的日誌增加了閱讀和分析的難度。

### 原始日誌範例

```
[2023-12-30 10:46:38,196: INFO/MainProcess] project: Sending due task test-nested-job (project.task.first_task)
[2023-12-30 10:46:38,219: INFO/MainProcess] Task project.task.first_task[dd1834ad-4af0-4ae3-bac4-41d90b8732ae] received
[2023-12-30 10:46:38,220: INFO/MainProcess] Debug task 1
[2023-12-30 10:46:38,267: INFO/MainProcess] Task project.task.second_debug_task[498bfe63-e072-44b9-be9f-5078bf78cca2] received
[2023-12-30 10:46:38,274: INFO/MainProcess] Task project.task.first_task[dd1834ad-4af0-4ae3-bac4-41d90b8732ae] succeeded in 0.05412780500000025s: None
[2023-12-30 10:46:38,276: INFO/MainProcess] Debug task 2
[2023-12-30 10:46:38,352: INFO/MainProcess] Task project.task.second_debug_task[a9edbc93-aa0c-45c4-8829-d7ef24fc50c1] received
[2023-12-30 10:46:38,367: INFO/MainProcess] Task project.task.second_debug_task[498bfe63-e072-44b9-be9f-5078bf78cca2] succeeded in 0.09155484199999986s: None
[2023-12-30 10:46:38,369: INFO/MainProcess] Debug task 2
[2023-12-30 10:46:38,442: INFO/MainProcess] Task project.task.third_debug_task[c59a94fb-5a74-40a8-93c0-9c36242f293f] received
[2023-12-30 10:46:38,461: INFO/MainProcess] Task project.task.second_debug_task[a9edbc93-aa0c-45c4-8829-d7ef24fc50c1] succeeded in 0.0920364410000003s: None
[2023-12-30 10:46:38,463: INFO/MainProcess] Debug task 3
[2023-12-30 10:46:38,527: INFO/MainProcess] Task project.task.fourth_debug_task[ac8dd0f7-edfc-458a-a089-6d4fc102c8bc] received
[2023-12-30 10:46:38,536: INFO/MainProcess] Task project.task.third_debug_task[c59a94fb-5a74-40a8-93c0-9c36242f293f] succeeded in 0.07286700600000007s: None
[2023-12-30 10:46:38,537: INFO/MainProcess] Debug task 4
[2023-12-30 10:46:38,576: INFO/MainProcess] Task project.task.third_debug_task[b174ad0c-7005-45af-a4a5-25362a9bb6ed] received
[2023-12-30 10:46:38,582: INFO/MainProcess] Task project.task.fourth_debug_task[ac8dd0f7-edfc-458a-a089-6d4fc102c8bc] succeeded in 0.04526384800000027s: None
[2023-12-30 10:46:38,583: INFO/MainProcess] Debug task 3
[2023-12-30 10:46:38,627: INFO/MainProcess] Task project.task.fourth_debug_task[ebfca86d-f5a0-4160-85d2-bbf3973b5e47] received
[2023-12-30 10:46:38,635: INFO/MainProcess] Task project.task.third_debug_task[b174ad0c-7005-45af-a4a5-25362a9bb6ed] succeeded in 0.052080793000000014s: None
[2023-12-30 10:46:38,636: INFO/MainProcess] Debug task 4
[2023-12-30 10:46:38,678: INFO/MainProcess] Task project.task.fourth_debug_task[b10dcf33-8493-4471-81c9-aec86a9a53c5] received
[2023-12-30 10:46:38,683: INFO/MainProcess] Task project.task.fourth_debug_task[ebfca86d-f5a0-4160-85d2-bbf3973b5e47] succeeded in 0.047611055000000846s: None
[2023-12-30 10:46:38,684: INFO/MainProcess] Debug task 4
[2023-12-30 10:46:38,725: INFO/MainProcess] Task project.task.fourth_debug_task[13d421f1-120e-4e41-804c-9133a9ef2a66] received
[2023-12-30 10:46:38,727: INFO/MainProcess] Task project.task.fourth_debug_task[b10dcf33-8493-4471-81c9-aec86a9a53c5] succeeded in 0.042970032999999574s: None
[2023-12-30 10:46:38,728: INFO/MainProcess] Debug task 4
[2023-12-30 10:46:38,769: INFO/MainProcess] Task project.task.fourth_debug_task[13d421f1-120e-4e41-804c-9133a9ef2a66] succeeded in 0.04080406000000103s: None
```

## 2. 初步優化：使用 asgi-correlation-id

為了解決這些問題，我們加入了一個叫做 [asgi-correlation-id](https://github.com/snok/asgi-correlation-id) 的 package，它能為每個任務產生一個獨特的識別碼，這樣一來，追蹤日誌就清楚多了。

### 解決方案的具體實施

```diff
# 在 project.main.py 中
+ load_correlation_ids()
+ load_celery_current_and_parent_ids(use_internal_celery_task_id=True)


# 在 project.celerylogging.py 中
+ @after_setup_logger.connect(weak=False)
+ def on_after_setup_logger(logger, *args, **kwargs):
+     handler = colorlog.StreamHandler()
+     handler.addFilter(correlation_id_filter)  # asgi_correlation_id.CorrelationIdFilter(...) 
+     handler.addFilter(celery_tracing_filter)  # asgi_correlation_id.CeleryTracingIdsFilter(...)
+     handler.setFormatter(formatter)    # colorlog.ColoredFormatter(...)
+     logger.handlers.clear()
+     logger.addHandler(handler)
```

### 優化後的日誌

```
   correlation-id          current-id
         |      parent-id      |
         |          |          |
INFO [????????] [????????] [????????] celery.beat            | Scheduler: Sending due task test-nested-job (project.task.first_task)
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.first_task[ea2e59f9-b293-4d64-bf65-f5125ebb97e1] received
INFO [95382411] [????????] [ea2e59f9] project.task           | Debug task 1
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.second_debug_task[09c23ded-8393-4951-9a03-42fffc830d17] received
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.second_debug_task[81407a8c-9c54-4538-acb3-a08fe5dde561] received
INFO [95382411] [????????] [ea2e59f9] celery.app.trace       | Task project.task.first_task[ea2e59f9-b293-4d64-bf65-f5125ebb97e1] succeeded in 0.03319657999963965s: None
INFO [95382411] [ea2e59f9] [09c23ded] project.task           | Debug task 2
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.third_debug_task[250b8b2e-1a84-409b-ac2a-14bb953bfff3] received
INFO [95382411] [ea2e59f9] [09c23ded] celery.app.trace       | Task project.task.second_debug_task[09c23ded-8393-4951-9a03-42fffc830d17] succeeded in 0.00590658700093627s: None
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.fourth_debug_task[461aac43-2619-48fa-8507-6942f56dc4aa] received
INFO [95382411] [ea2e59f9] [81407a8c] project.task           | Debug task 2
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.third_debug_task[5995d3e8-a378-410d-b83b-6f1b23e8bb10] received
INFO [95382411] [ea2e59f9] [81407a8c] celery.app.trace       | Task project.task.second_debug_task[81407a8c-9c54-4538-acb3-a08fe5dde561] succeeded in 0.006049554001947399s: None
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.fourth_debug_task[d10f49d0-2ee4-480c-9d9b-0bdbb9ea4c23] received
INFO [95382411] [09c23ded] [250b8b2e] project.task           | Debug task 3
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.fourth_debug_task[5e1f8022-89d5-432a-a674-10b29be0a557] received
INFO [95382411] [09c23ded] [250b8b2e] celery.app.trace       | Task project.task.third_debug_task[250b8b2e-1a84-409b-ac2a-14bb953bfff3] succeeded in 0.0036318539932835847s: None
INFO [95382411] [09c23ded] [461aac43] project.task           | Debug task 4
INFO [95382411] [09c23ded] [461aac43] celery.app.trace       | Task project.task.fourth_debug_task[461aac43-2619-48fa-8507-6942f56dc4aa] succeeded in 0.002018771003349684s: None
INFO [95382411] [81407a8c] [5995d3e8] project.task           | Debug task 3
INFO [????????] [????????] [????????] celery.worker.strategy | Task project.task.fourth_debug_task[f1dbfa52-9177-4ceb-a0fe-a00ce8a19de1] received
INFO [95382411] [81407a8c] [5995d3e8] celery.app.trace       | Task project.task.third_debug_task[5995d3e8-a378-410d-b83b-6f1b23e8bb10] succeeded in 0.0035413389996392652s: None
INFO [95382411] [81407a8c] [d10f49d0] project.task           | Debug task 4
INFO [95382411] [81407a8c] [d10f49d0] celery.app.trace       | Task project.task.fourth_debug_task[d10f49d0-2ee4-480c-9d9b-0bdbb9ea4c23] succeeded in 0.001998387997446116s: None
INFO [95382411] [250b8b2e] [5e1f8022] project.task           | Debug task 4
INFO [95382411] [250b8b2e] [5e1f8022] celery.app.trace       | Task project.task.fourth_debug_task[5e1f8022-89d5-432a-a674-10b29be0a557] succeeded in 0.0019207799996365793s: None
INFO [95382411] [5995d3e8] [f1dbfa52] project.task           | Debug task 4
INFO [95382411] [5995d3e8] [f1dbfa52] celery.app.trace       | Task project.task.fourth_debug_task[f1dbfa52-9177-4ceb-a0fe-a00ce8a19de1] succeeded in 0.0017463759941165335s: None
```

## 3. 深入問題分析：缺少 correlation_id 和 celery_current_id

### 3-1. Scheduler 發送任務日誌

在 Celery 的 `Scheduler` 類別中，`apply_entry` 函數在任務非同步執行之前進行日誌記錄。在這個時間點，`asgi_correlation_id.correlation_id` 和 `asgi_correlation_id.celery_current_id` 還未設置，導致日誌缺少關鍵的上下文信息，使得追蹤和調試任務變得困難。

```python
class Scheduler:
   ...
   def apply_entry(self, entry, producer=None):
       info('Scheduler: Sending due task %s (%s)', entry.name, entry.task)
       try:
           result = self.apply_async(entry, producer=producer, advance=False)
           ...
```

### 3-2. Celery Worker 處理接收任務日誌

在 Celery 的 `celery.worker.strategy.py` 的 `default` 函數中，`LOG_RECEIVED` 日誌記錄後才發出 `task_received` 信號。這導致日誌輸出與信號

```python
def default(task, app, consumer,
            info=logger.info, error=logger.error, task_reserved=task_reserved,
            to_system_tz=timezone.to_system, bytes=bytes,
            proto1_to_proto2=proto1_to_proto2):
    ...
    if _does_info:
        context = {
            'id': req.id,
            'name': req.name,
            'args': req.argsrepr,
            'kwargs': req.kwargsrepr,
            'eta': req.eta,
        }
        info(_app_trace.LOG_RECEIVED, context, extra={'data': context})
    ...
    signals.task_received.send(sender=consumer, request=req)
    ...
```

## 4. 解決方案

為了解決上述問題，我們採取了兩種策略：

1. **忽略接收日誌**：透過自定義的日誌過濾器，忽略那些缺乏關鍵上下文信息的日誌條目。這樣做的目的是為了減少冗餘信息，並集中關注於重要的日誌記錄。

```diff
+ class IgnoreSpecificLogFilter(logging.Filter):
+     def filter(self, record):
+         data = getattr(record, 'data', {})
+         if LOG_RECEIVED % {'name': data.get('name'), 'id': data.get('id')} == record.getMessage():
+             return False
+         return True

  @after_setup_logger.connect(weak=False)
  def on_after_setup_logger(logger, *args, **kwargs):
      ...
+     handler.addFilter(IgnoreSpecificLogFilter())
      ...
```

2. **重寫接收日誌**：在關鍵時刻重寫日誌，確保如 `correlation_id` 和 `celery_current_id` 等重要信息被及時記錄。這種做法提升了日誌的完整性，有助於更有效地追蹤任務。

```diff
+ @before_task_publish.connect(weak=False)
+ def on_before_task_publish(headers, properties, **kwargs):
+     if properties.get(SCHEDULER_TASK_FLAG_KEY) is True:
+         uid = uuid4().hex
+         asgi_correlation_id.correlation_id.set(uid)
+         headers['CORRELATION_ID'] = uid
+         getLogger(__name__).info('Scheduler: Sending due task %s (%s) in @before_task_publish', properties.get(SCHEDULED_TASK_NAME_KEY), headers.get('task'))
+         asgi_correlation_id.correlation_id.set(DEFAULT_UNSET_UUID)

+ @task_prerun.connect(weak=False)
+ def on_task_prerun(task, **kwargs):
+     # pylint: disable=logging-not-lazy
+     getLogger(__name__).info(LOG_RECEIVED % {'name': task.name,'id': task.request.id} + ' in @task_prerun')
```

### 調整後的日誌

```diff
+ INFO [95382411] [????????] [????????] project.celerylogging  | Scheduler: Sending due task test-nested-job (project.task.first_task) in @before_task_publish
+ INFO [95382411] [????????] [ea2e59f9] project.celerylogging  | Task project.task.first_task[ea2e59f9-b293-4d64-bf65-f5125ebb97e1] received in @task_prerun
  INFO [95382411] [????????] [ea2e59f9] project.task           | Debug task 1
+ INFO [95382411] [ea2e59f9] [09c23ded] celery.worker.strategy | Task project.task.second_debug_task[09c23ded-8393-4951-9a03-42fffc830d17] received in @task_prerun
+ INFO [95382411] [ea2e59f9] [81407a8c] celery.worker.strategy | Task project.task.second_debug_task[81407a8c-9c54-4538-acb3-a08fe5dde561] received in @task_prerun
  INFO [95382411] [????????] [ea2e59f9] celery.app.trace       | Task project.task.first_task[ea2e59f9-b293-4d64-bf65-f5125ebb97e1] succeeded in 0.03319657999963965s: None
  INFO [95382411] [ea2e59f9] [09c23ded] project.task           | Debug task 2
...
```



