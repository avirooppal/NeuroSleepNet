"""
nsn — import alias for neurosleepnet.

Both of these are identical:
    import nsn
    import neurosleepnet

Usage:
    import nsn
    nsn.init(project="my-agent")
    agent = nsn.wrap(your_slm)
"""
from neurosleepnet import *  # noqa: F401, F403
from neurosleepnet import (  # explicit re-exports for IDE autocomplete
    init,
    wrap,
    remember,
    recall,
    forget,
    forget_user,
    forget_project,
    pin,
    unpin,
    list_pins,
    feedback,
    feedback_batch,
    sleep,
    sleep_status,
    sleep_pause,
    sleep_resume,
    list_memories,
    search,
    stats,
    export,
    import_memories,
    merge_projects,   # Fix 7: was missing from explicit re-exports
    dashboard,
    context,
    get_embed,
    get_config,
    NSNAuthError,
    NSNConnectionError,
    NSNInitError,
)
