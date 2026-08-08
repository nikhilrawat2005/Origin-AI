"""
Import every model here so `Base.metadata.create_all()` (called from
app.core.database.init_db) always sees the full set of tables, even
though nothing else in the app imports these modules directly yet.
"""
from app.models.agent import Agent
from app.models.post import Post
from app.models.rejected_topic import RejectedTopic
from app.models.sources_cache import SourceCache
from app.models.breeth_mirror import BreethMirrorFact

__all__ = ["Agent", "Post", "RejectedTopic", "SourceCache", "BreethMirrorFact"]
