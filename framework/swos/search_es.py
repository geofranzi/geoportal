from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import (Date, Document, FacetedSearch, GeoShape, Index, Keyword, TermsFacet, Text,)
from elasticsearch_dsl.connections import connections

from webgis import settings


connections.create_connection(hosts=settings.ELASTICSEARCH_HOSTS)

class LayerIndex(Document):
    title = Text()
    category = Text(fields={'raw': Keyword()})
    topiccat = Keyword()
    description = Text()
    keywords = Text(fielddata=True, fields={'raw': Keyword()})
    wetland = Text(fielddata=True, fields={'raw': Keyword()})
    product_name = Text(fielddata=True, fields={'raw': Keyword()})
    indicator_name = Text(fielddata=True, fields={'raw': Keyword()})
    contact_person = Text(fielddata=True, fields={'raw': Keyword()})
    contact_org = Text(fielddata=True, fields={'raw': Keyword()})
    date_begin = Date()
    date_end = Date()
    lineage = Text()
    geom = GeoShape()

    class Meta:
        index = 'layer_index'

class ExternalDatabaseIndex(Document):
    name = Text()
    category = Text(fields={'raw': Keyword()})
    provided_information = Text()
    description = Text()
    continent = Text()
    country = Keyword()
    link = Text()
    wetland = Text(fielddata=True, fields={'raw': Keyword()})
    wetland_id = Text()

    class Meta:
        index = 'external_database_index'

class WetlandIndex(Document):
    title = Text()
    category = Text(fields={'raw': Keyword()})
    keywords = Text(fielddata=True, fields={'raw': Keyword()})
    wetland = Text(fielddata=True, fields={'raw': Keyword()})
    country = Keyword()
    partner = Text(fielddata=True, fields={'raw': Keyword()})
    ecoregion = Text(fielddata=True, fields={'raw': Keyword()})
    geom = GeoShape()

    class Meta:
        index = 'wetland_index'


class WetlandSearch(FacetedSearch):
    # indexes used for search
    doc_types = [ WetlandIndex, ExternalDatabaseIndex, LayerIndex  ]

    # fields that should be searched
    fields = [ 'title^2', 'description', 'topiccat', 'keywords', 'wetland', 'product_name', 'indicator_name', 'provided_information', 'name', 'contact_person', 'contact_org', 'lineage', 'country', 'partner', 'ecoregion']

    # use bucket aggregations to define facets
    facets = {
        'category': TermsFacet(field='category.raw'),
        'topiccat': TermsFacet(field='topiccat'),
        'keywords': TermsFacet(field='keywords.raw'),
        'wetland': TermsFacet(field='wetland.raw'),
        'product_name': TermsFacet(field='product_name.raw'),
        'indicator_name': TermsFacet(field='indicator_name.raw'),
        'contact_person': TermsFacet(field='contact_person.raw'),
        'contact_org': TermsFacet(field='contact_org.raw'),
        'ecoregion': TermsFacet(field='ecoregion.raw'),
    }

    # overwrite default query and to add fuzziness parameter and spatial search
    def query(self, search, er):
        q = super(WetlandSearch, self).search()

        # spatial search (ignore_unmapped=True --> ignore indexes without geom)
        if (self._query["south"] and self._query["north"] and self._query["east"] and self._query["west"]):
            search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND").filter(
                'geo_shape', ignore_unmapped="True", geom=
                {
                    "shape": {
                        "type": "envelope",
                        "coordinates": [[self._query["west"], self._query["south"]],
                                        [self._query["east"], self._query["north"]]]
                    },
                    "relation": "intersects"
                }
            )
        else:
            search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND")

        if (self._query["category"]):
            search_query = search_query.filter('term', category=self._query["category"])
        if (self._query["keywords"]):
            d = {'keywords.raw': self._query["keywords"]}
            search_query = search_query.filter('term', **d)
        if (self._query["topiccat"]):
            search_query = search_query.filter('term', topiccat=self._query["topiccat"])
        if (self._query["wetland"]):
            d = {'wetland.raw': self._query["wetland"]}
            search_query = search_query.filter('term', **d)
        if (self._query["product_name"]):
            d = {'product_name.raw': self._query["product_name"]}
            search_query = search_query.filter('term', **d)
        if(self._query["indicator_name"]):
            d = {'indicator_name.raw': self._query["indicator_name"]}
            search_query = search_query.filter('term', **d)
        if(self._query["contact_person"]):
            d = {'product_name.raw': self._query["contact_person"]}
            search_query = search_query.filter('term', **d)
        if (self._query["contact_org"]):
            d = {'contact_org.raw': self._query["contact_org"]}
            search_query = search_query.filter('term', **d)
        if (self._query["contact_person"]):
            d = {'ecoregion.raw': self._query["ecoregion"]}
            search_query = search_query.filter('term', **d)

        return search_query

#def search(search_text):
    #normale search
    # client = Elasticsearch()
    # s = Search().using(client).index("wetland_index").query("match", title="camargue").filter('geo_shape', geom=
    #      {
    #          "shape": {
    #              "type": "envelope",
    #              "coordinates": [[4.0, 43.0], [5.0, 42.0]]
    #          },
    #          "relation": "within"
    #      })
    #response = s.execute()
    #print response.__dict__
    #return response


# Index all
def bulk_indexing():
    from .models import (ExternalDatabase, ExternalLayer, Wetland, WetlandLayer,)
    es = Elasticsearch()

    layer_index = Index('layer_index')
    layer_index.delete(ignore=404)
    LayerIndex.init()
    [b.indexing() for b in WetlandLayer.objects.filter(publishable=True).iterator()]
    [b.indexing() for b in ExternalLayer.objects.filter(publishable=True).iterator()]

    external_database_index = Index('external_database_index')
    external_database_index.delete(ignore=404)
    ExternalDatabaseIndex.init()
    [b.indexing() for b in ExternalDatabase.objects.all().iterator()]

    wetland_index = Index('wetland_index')
    wetland_index.delete(ignore=404)
    WetlandIndex.init()
    # exclude wetlands with an invalid geometry (IDs: 9, 45, 49, 60)
    [b.indexing() for b in Wetland.objects.all().exclude(id__in = [45, 9, 49, 60]).iterator()]


# Delete index:  curl -XDELETE 'localhost:9200/layer_index?pretty'
# Show one entry: curl -XGET 'localhost:9200/layer_index/layer_index/2973?pretty'
# List all indexes: curl -XGET 'localhost:9200/_cat/indices?v&pretty'