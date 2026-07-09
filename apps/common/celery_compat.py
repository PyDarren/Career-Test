"""Celery compatibility shim.

Provides a no-op ``shared_task`` decorator when Celery is not installed,
so that task modules can be imported without errors in environments
where Celery is unavailable (e.g. during unit tests on a CI server
without the full dependency stack).

When Celery IS installed, the real ``shared_task`` is used.
"""

try:
    from celery import shared_task  # type: ignore[import-untyped]
except ImportError:
    def shared_task(*args, **kwargs):
        """No-op fallback when Celery is not installed.

        Supports both ``@shared_task`` and ``@shared_task(name='...')``
        usage patterns.
        """
        if len(args) == 1 and callable(args[0]) and not kwargs:
            # Used as @shared_task without parentheses
            return args[0]

        def decorator(func):
            # Attach a dummy .delay method so code that calls
            # task.delay() doesn't crash (it will run synchronously).
            def delay(*d_args, **d_kwargs):
                return func(*d_args, **d_kwargs)

            def apply_async(*a_args, **a_kwargs):
                return func()

            func.delay = delay
            func.apply_async = apply_async
            return func

        return decorator
