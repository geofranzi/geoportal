from elasticsearch_dsl import (Completion, Date, Document, FacetedSearch, GeoShape, Integer, Keyword, Nested,
                               NestedFacet, Q, TermsFacet, Text, connections,)


# Connect with es on port
# Todo error handling if not available


# connections.create_connection(hosts='http://localhost:9200', timeout=20)
connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)


class ClimateDatasetsIndex(Document):
    title = Text(fielddata=True, fields={'keyword': Keyword(), 'completion': Completion()})
    dataset_id = Integer()
    variable_standard_name_cf = Keyword()
    variable_name = Keyword()
    frequency = Keyword()
    scenario = Keyword()
    gcm = Keyword()
    rcm = Keyword()
    bias_correction = Keyword()
    contact_person = Text(fielddata=True, fields={'raw': Keyword()})
    contact_org = Text(fielddata=True, fields={'raw': Keyword()})
    date_begin = Date()
    date_end = Date()
    lineage = Text()
    geom = GeoShape()
    link = Text()

    class Index:
        name = 'climate_index'


class ClimateDatasetsCollectionIndex(Document):
    frequency = Keyword()
    scenario = Keyword()
    gcm = Keyword()
    rcm = Keyword()
    bias_correction = Keyword()
    processing_method = Keyword() 
    variables = Nested(
        multi=True,
        properties={
            'variable_abbr': Text(fielddata=True, fields={'keyword': Keyword()}),
            'file_id': Text(fielddata=True, fields={'keyword': Keyword()}),
        }
    )

    class Index:
        name = 'climate_collection_index'

class ClimateIndicatorIndex(Document):
    frequency = Keyword()
    scenario = Keyword()
    gcm = Keyword()
    rcm = Keyword()
    indicator = Keyword()
    year_begin = Keyword()
    year_end = Keyword()
    periode = Keyword()
    title = Keyword()
    dataset = Keyword()
    variables = Nested(
        multi=True,
        properties={
            'variable_abbr': Text(fielddata=True, fields={'keyword': Keyword()}),
            'file_id': Text(fielddata=True, fields={'keyword': Keyword()}),
        }
    )

    class Index:
        name = 'climate_indicator_index'



class ClimateSearch(FacetedSearch):
    index = 'climate_index'
    doc_types = [ClimateDatasetsIndex, ]
    fields = ['title^5']

    facets = {
        'title': TermsFacet(field='title', size=100),
        'variable_standard_name_cf': TermsFacet(field='variable_standard_name_cf', size=100),
        'processing_method': TermsFacet(field='processing_method', size=100),
        'variable_name': TermsFacet(field='variable_name', size=100),
        'Variable_abbr': TermsFacet(field='Variable_abbr', size=100),
        'frequency': TermsFacet(field='frequency', size=100),
        'scenario': TermsFacet(field='scenario', size=100),
        'gcm': TermsFacet(field='gcm', size=100),
        'rcm': TermsFacet(field='rcm', size=100),
        'bias_correction': TermsFacet(field='bias_correction', size=100),
        'start_year': TermsFacet(field='start_year', size=100),
        'end_year': TermsFacet(field='end_year', size=100)
    }

    # overwrite default query and to add fuzziness parameter and spatial search
    def query(self, search, er):
        q = super(ClimateSearch, self).search()

        # spatial search (ignore_unmapped=True --> ignore indexes without geom)
        if (self._query["south"] and self._query["north"] and self._query["east"] and self._query["west"]):
            search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND").filter(
                'geo_shape', ignore_unmapped="True", geom=  # noqa: E251
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

        if (self._query["variable_standard_name_cf"]):
            d = {'variable_standard_name_cf': self._query["variable_standard_name_cf"]}
            search_query = search_query.filter('term', **d)
        if (self._query["gcm"]):
            d = {'gcm.raw': self._query["gcm"]}
            search_query = search_query.filter('term', **d)
        if (self._query["rcm"]):
            d = {'rcm.raw': self._query["rcm"]}
            search_query = search_query.filter('term', **d)
        if (self._query["variable_name"]):
            d = {'variable_name': self._query["variable_name"]}
            search_query = search_query.filter('term', **d)
        print(search_query.to_dict())
        return search_query


class ClimateCollectionSearch(FacetedSearch):
    index = 'climate_collection_index'
    doc_types = [ClimateDatasetsIndex, ]
    fields = ['title^5', 'gcm']

    facets = {
        'title': TermsFacet(field='title', size=100),
        'variable_abbr': NestedFacet('variables', TermsFacet(field='variables.variable_abbr.keyword', size=300)),
        'file_id': NestedFacet('variables', TermsFacet(field='variables.file_id', size=300)),
        'frequency': TermsFacet(field='frequency', size=100),
        'scenario': TermsFacet(field='scenario', size=100),
        'gcm': TermsFacet(field='gcm', size=100),
        'rcm': TermsFacet(field='rcm', size=100),
        'processing_method': TermsFacet(field='processing_method', size=100),
        'start_year': TermsFacet(field='start_year', size=100),
        'end_year': TermsFacet(field='end_year', size=100)
    }

    # overwrite default query and to add fuzziness parameter and spatial search
    def query(self, search, er):
        q = super(ClimateCollectionSearch, self).search()
        search_query = q
        # spatial search (ignore_unmapped=True --> ignore indexes without geom)
        if self._query["south"] and self._query["north"] and self._query["east"] and self._query["west"]:
            search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND").filter(
                'geo_shape', ignore_unmapped="True", geom=  # noqa: E251
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
            if self._query["text"]:
                search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND")

        if self._query["variable_abbr"]:
            for var in self._query["variable_abbr"].split(","):
                d = {'variables.variable_abbr.keyword': var}
                search_query = search_query.filter(
                    'nested', path='variables',
                    query=Q(
                        'term', **d
                    ))

        if self._query["gcm"]:
            for gmc in self._query["gcm"].split(","):
                d = {'gcm': gmc}
                search_query = search_query.filter('term', **d)

        if self._query["rcm"]:
            for rcm in self._query["rcm"].split(","):
                d = {'rcm': rcm}
                search_query = search_query.filter('term', **d)

        if self._query["processing_method"]:
            for processing_method in self._query["processing_method"].split(","):
                d = {'processing_method': processing_method}
                search_query = search_query.filter('term', **d)

        print(search_query.to_dict())
        return search_query
        
class ClimateIndicatorSearch(FacetedSearch):
    index = 'climate_indicator_index'
    doc_types = [ClimateIndicatorIndex, ]
    fields = ['title^5', 'gcm']

    facets = {
        'dataset': TermsFacet(field='dataset', size=200),
        'variable_abbr': NestedFacet('variables', TermsFacet(field='variables.variable_abbr.keyword', size=300)),
        'file_id': NestedFacet('variables', TermsFacet(field='variables.file_id', size=300)),
        'frequency': TermsFacet(field='frequency', size=100),
        'scenario': TermsFacet(field='scenario', size=100),
        'gcm': TermsFacet(field='gcm', size=100),
        'rcm': TermsFacet(field='rcm', size=100),
        'indicator': TermsFacet(field='indicator', size=100),
        'year_begin': TermsFacet(field='year_begin', size=100),
        'year_end': TermsFacet(field='year_end', size=100),
        'periode': TermsFacet(field='periode', size=100),
        'title': TermsFacet(field='title', size=200),

    }

    # overwrite default query and to add fuzziness parameter and spatial search
    def query(self, search, er):
        q = super(ClimateIndicatorSearch, self).search()
        search_query = q
        # spatial search (ignore_unmapped=True --> ignore indexes without geom)
        if self._query["south"] and self._query["north"] and self._query["east"] and self._query["west"]:
            search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND").filter(
                'geo_shape', ignore_unmapped="True", geom=  # noqa: E251
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
            if self._query["text"]:
                search_query = q.query("multi_match", fields=self.fields, query=self._query["text"], fuzziness="AUTO", operator="AND")

        if self._query["variable_abbr"]:
            for var in self._query["variable_abbr"].split(","):
                d = {'variables.variable_abbr.keyword': var}
                search_query = search_query.filter(
                    'nested', path='variables',
                    query=Q(
                        'term', **d
                    ))

        if self._query["gcm"]:
            for gmc in self._query["gcm"].split(","):
                d = {'gcm': gmc}
                search_query = search_query.filter('term', **d)

        if self._query["rcm"]:
            for rcm in self._query["rcm"].split(","):
                d = {'rcm': rcm}
                search_query = search_query.filter('term', **d)

        if self._query["indicator"]:
            for indicator in self._query["indicator"].split(","):
                d = {'indicator': indicator}
                search_query = search_query.filter('term', **d)

        if self._query["scenario"]:
            for scenario in self._query["scenario"].split(","):
                d = {'scenario': scenario}
                search_query = search_query.filter('term', **d)

        if self._query["year_begin"]:
            for year_begin in self._query["year_begin"].split(","):
                d = {'year_begin': year_begin}
                search_query = search_query.filter('term', **d)

        if self._query["year_end"]:
            for year_end in self._query["year_end"].split(","):
                d = {'year_end': year_end}
                search_query = search_query.filter('term', **d)

        if self._query["periode"]:
            for periode in self._query["periode"].split(","):
                d = {'periode': periode}
                search_query = search_query.filter('term', **d)

        if self._query["dataset"]:
            for dataset in self._query["dataset"].split(","):
                d = {'dataset': dataset}
                search_query = search_query.filter('term', **d)

        print(search_query.to_dict())
        return search_query
