__author__ = "mtianyan"
__date__ = "2017/6/25 10:18"

from elasticsearch_dsl import (
    connections,
    Document,
    Text,
    Keyword,
    Integer,
    Date,
    Completion,
    analyzer,
)

connections.create_connection(hosts=["localhost"])

my_analyzer = analyzer("ik_smart")


class LagouJobIndex(Document):
    suggest = Completion(analyzer=my_analyzer)
    title = Text(analyzer="ik_max_word")
    url = Keyword()
    url_object_id = Keyword()
    publish_time = Date()
    job_advantage = Text(analyzer="ik_max_word")
    job_desc = Text(analyzer="ik_smart")
    job_addr = Text(analyzer="ik_max_word")
    company_name = Keyword()
    company_url = Keyword()
    tags = Text(analyzer="ik_max_word")
    crawl_time = Date()

    class Index:
        name = "lagou_job"
