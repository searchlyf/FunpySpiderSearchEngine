__author__ = "mtianyan"
__date__ = "2018/8/20 05:46"

import datetime
import re
import scrapy
from elasticsearch_dsl import connections
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose, Join
from w3lib.html import remove_tags
from FunpySpiderSearch.items import MysqlItem, ElasticSearchItem
from FunpySpiderSearch.settings import SQL_DATETIME_FORMAT
from FunpySpiderSearch.sites.lagou.es_lagou import LagouJobIndex
from FunpySpiderSearch.utils.es_utils import generate_suggests
from FunpySpiderSearch.utils.mysql_utils import fun_sql_insert

es_lagou_job = connections.create_connection(LagouJobIndex)
JOB_COUNT_INIT = 0


class LagouJobItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


def remove_splash(value):
    # 去掉工作城市的斜线
    return value.replace("/", "")


def handle_job_addr(value):
    addr_list = value.split("\n")
    addr_list = [item.strip() for item in addr_list if item.strip() != "查看地图"]
    return "".join(addr_list)


class LagouJobItem(scrapy.Item, MysqlItem, ElasticSearchItem):
    title = scrapy.Field()
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    publish_time = scrapy.Field()
    job_advantage = scrapy.Field()
    job_desc = scrapy.Field()
    job_addr = scrapy.Field(input_processor=MapCompose(remove_tags, handle_job_addr))
    company_name = scrapy.Field()
    company_url = scrapy.Field()
    tags = scrapy.Field(input_processor=Join(","))
    crawl_time = scrapy.Field()
    crawl_update_time = scrapy.Field()

    def clean_data(self):

        """try catch 大法修复tags问题"""
        try:
            self["tags"] = self["tags"]
            self["publish_time"] = self["publish_time"]
            self["title"] = self["title"]
        except KeyError:
            self["tags"] = ""
            self["publish_time"] = ""
            self["title"] = ""
        match_time1 = re.match("(\d+):(\d+).*", self["publish_time"])
        match_time2 = re.match("(\d+)天前.*", self["publish_time"])
        match_time3 = re.match("(\d+)-(\d+)-(\d+)", self["publish_time"])
        if match_time1:
            today = datetime.datetime.now()
            hour = int(match_time1.group(1))
            minutues = int(match_time1.group(2))
            time = datetime.datetime(today.year, today.month, today.day, hour, minutues)
            self["publish_time"] = time.strftime(SQL_DATETIME_FORMAT)
        elif match_time2:
            days_ago = int(match_time2.group(1))
            today = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            self["publish_time"] = today.strftime(SQL_DATETIME_FORMAT)
        elif match_time3:
            year = int(match_time3.group(1))
            month = int(match_time3.group(2))
            day = int(match_time3.group(3))
            today = datetime.datetime(year, month, day)
            self["publish_time"] = today.strftime(SQL_DATETIME_FORMAT)
        else:
            self["publish_time"] = datetime.datetime.now().strftime(SQL_DATETIME_FORMAT)
        self["crawl_time"] = self["crawl_time"].strftime(SQL_DATETIME_FORMAT)

    def save_to_mysql(self):
        self.clean_data()
        insert_sql = """
                    insert into lagou_job(title, url, url_object_id, work_years_min, work_years_max,
                    publish_time, job_advantage, job_desc, job_addr, company_name, company_url,
                    tags, crawl_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE  job_desc=VALUES(job_desc)
                """
        sql_params = (
            self["title"],
            self["url"],
            self["url_object_id"],
            self["publish_time"],
            self["job_advantage"],
            self["job_desc"],
            self["job_addr"],
            self["company_name"],
            self["company_url"],
            self["tags"],
            self["crawl_time"],
        )

        return insert_sql, sql_params

    def save_to_es(self):
        self.clean_data()
        job = LagouJobIndex()
        job.title = self["title"]
        job.url = self["url"]
        job.meta.id = self["url_object_id"]
        job.job_desc = (
            remove_tags(self["job_desc"]).strip().replace("\r\n", "").replace("\t", "")
        )
        job.job_advantage = self["job_advantage"]
        job.tags = self["tags"]
        job.publish_time = self["publish_time"]
        job.job_addr = self["job_addr"]
        job.company_name = self["company_name"]
        job.company_url = self["company_url"]
        job.crawl_time = self["crawl_time"]

        job.suggest = generate_suggests(
            es_lagou_job,
            (
                (job.title, 10),
                (job.tags, 7),
                (job.job_advantage, 6),
                (job.job_desc, 3),
                (job.job_addr, 5),
                (job.company_name, 8),
            ),
        )
        job.save()

    def help_fields(self):
        for field in self.field_list:
            print(field, "= scrapy.Field()")


if __name__ == "__main__":
    LagouJobItem().help_fields()
    instance = LagouJobItem()
    sql, params = fun_sql_insert(
        field_list=instance.field_list,
        duplicate_key_update=instance.duplicate_key_update,
        table_name=instance.table_name,
    )
