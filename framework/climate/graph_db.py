from io import BytesIO

import requests


# Accept header / different response for SPARQL queries
headers = {
    "Accept": "application/sparql-results+json, application/sparql-results+xml, text/turtle"
}

repo_name = "repo"
# Set the repository name and the URL of the GraphDB server
graphdb_url = "http://localhost:7200"


def send_request(query):
    response = requests.post(
        graphdb_url + "/repositories/" + repo_name,
        data={"query": query},
        headers=headers
    )

    if response.status_code == 200:
        print("Query executed successfully.")
    else:
        print("Error executing query:", response.status_code)
    print("Response:", response.text)
    return response


def create_repo(repo_name):
    repo_config_ttl = """
   #
#RDF4J configuration template for a GraphDB repository
# This template is intended as an example only
#
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID """ + repo_name + """ ;
    rdfs:label "Sample repository TTL file." ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;

            graphdb:read-only "false" ;

            # Inference and Validation
            graphdb:ruleset "rdfsplus-optimized" ;
            graphdb:disable-sameAs "true" ;
            graphdb:check-for-inconsistencies "false" ;

            # Indexing
            graphdb:entity-id-size "32" ;
            graphdb:enable-context-index "false" ;
            graphdb:enablePredicateList "true" ;
            graphdb:enable-fts-index "false" ;
            graphdb:fts-indexes ("default" "iri") ;
            graphdb:fts-string-literals-index "default" ;
            graphdb:fts-iris-index "none" ;

            # Queries and Updates
            graphdb:query-timeout "0" ;
            graphdb:throw-QueryEvaluationException-on-timeout "false" ;
            graphdb:query-limit-results "0" ;

            # Settable in the file but otherwise hidden in the UI and in the RDF4J console
            graphdb:base-URL "http://example.org/owlim#" ;
            graphdb:defaultNS "" ;
            graphdb:imports "" ;
            graphdb:repository-type "file-repository" ;
            graphdb:storage-folder "storage" ;
            graphdb:entity-index-size "10000000" ;
            graphdb:in-memory-literal-properties "true" ;
            graphdb:enable-literal-index "true" ;
        ]
    ].

    """
    # Fake a file upload using BytesIO
    files = {
        'config': ('repo-config.ttl', BytesIO(repo_config_ttl.encode('utf-8')), 'application/x-turtle')
    }

    url = "http://localhost:7200/rest/repositories"

    # POST request
    response = requests.post(url, files=files)

    print("Status:", response.status_code)
    print("Response:", response.text)


def import_data(file, repo_name):
    with open(file, "rb") as ttl_file:
        response = requests.post(
            f"http://localhost:7200/repositories/{repo_name}/statements",
            headers={"Content-Type": "application/x-turtle"},
            data=ttl_file
        )

    print("Import status:", response.status_code)
    print("Response:", response.text)


def test_repo():
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100
    """

    response = send_request(query)

    print(response.json())


def subquery(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
    CONSTRUCT {
        ?activity ?p ?o .

        ?entity prov:qualifiedGeneration ?gen .
        ?gen ?p3 ?o3 .
        ?entity prov:wasAttributedTo ?agent .
        ?agent ?p4 ?o4 .
        ?activity prov:wasAssociatedWith ?software .
        ?software ?p5 ?o5 .
        ?collection prov:hadMember ?entity .
    }
    WHERE { tippecc_data:""" + entity + """
        prov:qualifiedGeneration/prov:activity ?baseActivity .
        ?baseActivity prov:wasInformedBy* ?activity .

        OPTIONAL { ?activity ?p ?o .
            OPTIONAL {
                     ?activity prov:wasAssociatedWith ?software .
                     ?software ?p5 ?o5 .
              }
         }
            OPTIONAL {
              ?activity prov:used ?entity .

              OPTIONAL {
                     ?entity prov:qualifiedGeneration ?gen .
                     ?gen ?p3 ?o3 .
              }
              OPTIONAL {
                     ?entity prov:wasAttributedTo ?agent .
                     ?agent ?p4 ?o4 .
              }
              OPTIONAL {
                     ?collection prov:hadMember ?entity .

              }
            }
    }

    """

    send_request(query)


def subquery_entity_meta(entity):
    query = """
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
        CONSTRUCT {
            ?entity ?p8 ?o8 .
        }
        WHERE { tippecc_data:""" + entity + """
            prov:qualifiedGeneration/prov:activity ?baseActivity .
            ?baseActivity prov:wasInformedBy* ?activity .

                OPTIONAL {
                  ?activity prov:used ?entity .
                ?entity ?p8 ?o8 .
                }
        }
    """

    response = send_request(query)
    return response.json()


def subquery_collection_meta(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
      PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
      CONSTRUCT {

    ?collection ?p7 ?o7 .

      }
      WHERE { tippecc_data:""" + entity + """
        prov:qualifiedGeneration/prov:activity ?baseActivity .
        ?baseActivity prov:wasInformedBy* ?activity .

          OPTIONAL {
               OPTIONAL {
                          ?activity prov:wasAssociatedWith ?software .
                   }
           }
              OPTIONAL {
              ?activity prov:used ?entity .

              OPTIONAL {
                     ?entity prov:qualifiedGeneration ?gen .
              }
              OPTIONAL {
                     ?entity prov:wasAttributedTo ?agent .
              }
              OPTIONAL {
                     ?collection prov:hadMember ?entity .
                ?collection ?p7 ?o7 .
            FILTER(?p7 != prov:hadMember)  # Exclude 'hadMember' relations
              }
            }
    }

    """

    response = send_request(query)
    print("Response:", response.text)


def count_prov(entity):
    query = """
     PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>

SELECT   (COUNT(DISTINCT ?entity) AS ?entityCount)
  (COUNT(DISTINCT ?activity) AS ?activityCount)
  (COUNT(DISTINCT ?agent) AS ?agentCount)
 (COUNT(DISTINCT ?software) AS ?softwareCount)
 (COUNT(DISTINCT ?collection) AS ?collectionCount)
WHERE {
  tippecc_data:""" + entity + """
    prov:qualifiedGeneration/prov:activity ?baseActivity .

  ?baseActivity prov:wasInformedBy* ?activity .
  OPTIONAL {
    ?activity prov:wasAssociatedWith ?software .
  }
  OPTIONAL {
    ?activity prov:used ?entity .
    OPTIONAL {
      ?entity prov:qualifiedGeneration ?gen .
    }
    OPTIONAL {
      ?entity prov:wasAttributedTo ?agent .
    }
    OPTIONAL {
      ?collection prov:hadMember ?entity .
    }
  }
}
    """

    response = send_request(query)
    print(response.json())
    return response.json()


def source_entities(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
    SELECT  DISTINCT ?entity ?file_size ?collection_id ?num_time_steps
    WHERE { tippecc_data:""" + entity + """
        prov:qualifiedGeneration/prov:activity ?baseActivity .

        ?baseActivity prov:wasInformedBy* ?activity .
        OPTIONAL {
            ?activity prov:used ?entity .


        OPTIONAL {?entity tippecc_data:file_size ?file_size}
        OPTIONAL {?entity tippecc_data:collection_id ?collection_id}
        OPTIONAL {?entity tippecc_data:num_time_steps ?num_time_steps}
}
        FILTER NOT EXISTS {
            ?entity prov:wasDerivedFrom [] .
        }

    }
    """

    response = send_request(query)
    print(response.json())
    return response.json()


def result_entities(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
    SELECT  DISTINCT ?entity ?file_size ?collection_id ?num_time_steps
    WHERE { tippecc_data:""" + entity + """
        prov:qualifiedGeneration/prov:activity ?baseActivity .

        ?baseActivity prov:wasInformedBy* ?activity .
        OPTIONAL {
            ?activity prov:used ?entity .


        OPTIONAL {?entity tippecc_data:file_size ?file_size}
        OPTIONAL {?entity tippecc_data:collection_id ?collection_id}
        OPTIONAL {?entity tippecc_data:num_time_steps ?num_time_steps}
}
        FILTER EXISTS {
            ?entity prov:wasDerivedFrom [] .
        }
    }
    """

    response = send_request(query)
    print(response.json())
    return response.json()


def base_for_entities(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
    SELECT Distinct ?entity ?file_size ?collection_id ?num_time_steps
    WHERE {
        ?entity prov:wasDerivedFrom* tippecc_data:""" + entity + """ .

        OPTIONAL {?entity tippecc_data:file_size ?file_size}
        OPTIONAL {?entity tippecc_data:collection_id ?collection_id}
        OPTIONAL {?entity tippecc_data:num_time_steps ?num_time_steps}

        FILTER (?entity != tippecc_data:""" + entity + """)
    }
    """

    response = send_request(query)
    print(response.json())
    return response.json()


def activities(entity):
    query = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX tippecc_data: <http://www.provbook.org/tippecc/data/>
    SELECT  DISTINCT ?activities ?p ?o
    WHERE { tippecc_data:""" + entity + """
        prov:qualifiedGeneration/prov:activity ?baseActivity .

        ?baseActivity prov:wasInformedBy* ?activity .
        ?activity ?p ?o .
    }
    """

    response = send_request(query)
    print(response.json())
    return response.json()
