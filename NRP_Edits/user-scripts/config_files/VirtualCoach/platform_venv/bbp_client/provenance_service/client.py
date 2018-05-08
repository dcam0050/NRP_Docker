'''python client for the provenance services'''
import collections
import logging
import requests
from os.path import join as joinp

from bbp_services.client import get_services
import bbp_client.swagger_helpers as sh
from bbp_client.oidc.client import BBPOIDCClient
from bbp_client.provenance_service.swagger import swagger
from bbp_client.provenance_service.swagger import ActivityApi, AgentApi, EntityApi
from bbp_client.provenance_service.exceptions import ProvException

L = logging.getLogger(__name__)


class Client(object):
    '''Interface to the platform provenance service via python.

       provenance model is defined in http://www.w3.org/TR/2013/REC-prov-dm-20130430/

        Example:
            >>> #you'll likely need a user for authentication
            >>> user = 'gevaert'
            >>> server = 'http://localhost:8888'
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> client = BBPOIDCClient.implicit_auth(user)
            >>> from bbp_client.provenance_service.client import Client
            >>> ps = Client(server, client)
            >>> ps.get_activities(predicate='"bbp:jobId"="44f8c20a-d518-11e3-ac11-0050569721c6"')

    '''
    def __init__(self, host, oauth_client=None, headers=None):
        '''
        Args:
            host: the protocol and name, 'http://localhost:port
            oauth_client: instance of the bbp_client.oidc.client
            headers: HTTP headers passed to server
        '''
        #mangle server and port
        self.host = host
        self.oauth_client = oauth_client
        self.headers = headers or {}

        if self.oauth_client:
            self.headers['Authorization'] = self.oauth_client.get_auth_header()
        self.headers['User-Agent'] = 'py_provenance_service_client'

        self._api = swagger.ApiClient('api_key', host)
        sh.patch_swagger_callapi(self._api, self._get_headers)

        self._activity = ActivityApi.ActivityApi(self._api)
        self._agent = AgentApi.AgentApi(self._api)
        self._entity = EntityApi.EntityApi(self._api)

    @classmethod
    def new(cls, environment='prod', user=None, password=None, token=None):
        '''create new provenance service client'''
        services = get_services()
        oauth_url = services['oidc_service'][environment]['url']
        prov_url = services['prov_service'][environment]['url']
        if token:
            oauth_client = BBPOIDCClient.bearer_auth(oauth_url, token)
        else:
            oauth_client = BBPOIDCClient.implicit_auth(user, password, oauth_url)
        return cls(prov_url, oauth_client)

    def _get_headers(self):
        '''return the headers required for the http call'''
        #TODO, when to do client refresh?
        #self.client.refresh()
        return self.headers

    @staticmethod
    def _get_fields(predicate, path):
        ''' convert positioned parameters to dictionary '''
        query_fields = {'predicate': predicate}
        if path:
            query_fields['path'] = path
        return query_fields

    @sh.swagger_error
    def get_agents(self, predicate, path=None):
        ''' retrieve a set of agents matching predicate and complete it by path.

        retrieve a set of agents as defined in
        http://www.w3.org/TR/2013/REC-prov-dm-20130430/#term-agent
        matching a predicate and returns a prov-json serialization of it .

        complete this list by navigation through the list of path expression contained
        in the path argument and starting from the retrieved set of agents.

        Args:
            predicate (str): a predicate to match.

                a string in the form of: "field1"="valueA" or "field2"="valueB".

                possible fields are:

                - prov:type (string). possible values: prov:Person or prov:Software agent.
                - bbp:auth_type (string). possible values:  bbp:gaspar
                - bbp:value (string). a sciper id in the case of bbp:gaspar

                example :
                  "bbp:value"="1234" or "bbp:value"="4567" or "bbp:value"="8901"
            path (str, optional): a set of path expression completing the matched agents.

                objects in the path will be returned too.

                a string in the form of a comma separated list of path expressions.

                a path expression is dot separated list of path elements.

                a path element can be in:

                - usingActivity
                - usedEntity
                - generatedEntity
                - generatingActivity
                - derivatingEntity
                - derivatedEntity
                - derivatedFromEntity
                - derivatedToEntity
                - derivatedFromActivity
                - derivatedByActivity
                - triggeredEntity
                - triggeringEntity
                - startingActivity
                - startedActivity
                - triggeringActivity
                - triggeredActivity
                - activityResponsible
                - activityDelegated
                - delegatedForActivity
                - responsible
                - responsibleForActivity
                - delegated
                - associatedActivity
                - associatedAgent

                example :

                associatedAgent,responsibleForActivity.generatedEntity
        Returns:
            a prov-json serialization of the matching agents.

            the complete schema is defined in
            http://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
        '''
        query_fields = Client._get_fields(predicate, path)
        prov_json = self._agent.get_agent(**query_fields)
        return prov_json

    @sh.swagger_error
    def get_activities(self, predicate, path=None):
        ''' retrieve a set of activities matching predicate and complete it by path.

        retrieve a set of activities as defined in
        http://www.w3.org/TR/2013/REC-prov-dm-20130430/#term-activity
        matching a predicate and returns a prov-json serialization of it .

        complete this list by navigation through the list of path expression contained in
        the path argument and starting from the retrieved set of activities.

        Args:
            predicate (str): a predicate to match.

                a string in the form of: "field1"="valueA" or "field2"="valueB".

                possible fields are:
                - bbp:job (string), a uuid for a job id
                - bbp:status (string), a job status
                - prov:startTime (string), the start time as an iso 8601 format
                - prov:endTime (string), the end time as an iso 8601 format

                example :

                "bbp:job"="44f8c20a-d518-11e3-ac11-0050569721c6"

            path (str, optional): a set of path expression completing the matched activities.

                objects in the path will be returned too.

                a string in the form of a comma separated list of path expressions.

                a path expression is dot separated list of path elements.

                a path element can be in:

                - usingActivity
                - usedEntity
                - generatedEntity
                - generatingActivity
                - derivatingEntity
                - derivatedEntity
                - derivatedFromEntity
                - derivatedToEntity
                - derivatedFromActivity
                - derivatedByActivity
                - triggeredEntity
                - triggeringEntity
                - startingActivity
                - startedActivity
                - triggeringActivity
                - triggeredActivity
                - activityResponsible
                - activityDelegated
                - delegatedForActivity
                - responsible
                - responsibleForActivity
                - delegated
                - associatedActivity
                - associatedAgent

                example :

                usedEntity,generatedEntity.usingActivity
        Returns:
            a prov-json serialization of the matching activities.

            the complete schema is defined in \
            http://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
        '''
        query_fields = Client._get_fields(predicate, path)
        prov_json = self._activity.get_activity(**query_fields)
        return prov_json

    @sh.swagger_error
    def get_entities(self, predicate, path=None):
        ''' retrieve a set of entities matching predicate and complete it by path.

        retrieve a set of entities as defined in
        http://www.w3.org/TR/2013/REC-prov-dm-20130430/#term-entity matching a predicate
        and returns a prov-json serialization of it .

        complete this list by navigation through the list of path expression
        contained in the path argument and starting from the retrieved set of entities.

        Args:
            predicate (str): a predicate to match.

                a string in the form of: "field1"="valueA" or "field2"="valueB".

                possible fields are:

                - prov:role (string). bbp:value or bbp:document.
                - prov:value (string). a serialization of the value or the url.
                - bbp:ontologyname (string). a ontology identifier.

                example :

                "bbp:job"="44f8c20a-d518-11e3-ac11-0050569721c6"

            path (str, optional): a set of path expression completing the matched activities.

                objects in the path will be returned too.

                a string in the form of a comma separated list of path expressions.

                a path expression is dot separated list of path elements.

                a path element can be in:

                - usingActivity
                - usedEntity
                - generatedEntity
                - generatingActivity
                - derivatingEntity
                - derivatedEntity
                - derivatedFromEntity
                - derivatedToEntity
                - derivatedFromActivity
                - derivatedByActivity
                - triggeredEntity
                - triggeringEntity
                - startingActivity
                - startedActivity
                - triggeringActivity
                - triggeredActivity
                - activityResponsible
                - activityDelegated
                - delegatedForActivity
                - responsible
                - responsibleForActivity
                - delegated
                - associatedActivity
                - associatedAgent

                example :

                derivatedToEntity,usingActivity.generatedEntity.usingActivity
        Returns:
            a prov-json serialization of the matching entities.

            the complete schema is defined in
            http://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
        '''
        query_fields = Client._get_fields(predicate, path)
        prov_json = self._entity.get_entity(**query_fields)
        return prov_json

    @staticmethod
    def _get_expand_fields(predicate, direction, depth, relation, complete):
        ''' converts the positioned parameters for expand to a dictionary '''
        query_fields = {'predicate': predicate}
        if direction:
            query_fields['direction'] = direction
        if depth:
            query_fields['depth'] = depth
        if relation:
            query_fields['relation'] = relation
        if complete:
            query_fields['complete'] = complete
        return query_fields

    @sh.swagger_error
    def expand_activities(self, predicate, direction='both',
                          depth=1, relation='usage', complete=None):
        ''' retrieve a set of activities matching predicate and expand it following a relation.

        retrieve a set of activities as defined in
        http://www.w3.org/TR/2013/REC-prov-dm-20130430/#term-activity
        matching a predicate and returns a prov-json serialization of it .

        expand the list of activities by navigating to next activity
        following a invocation relationship or a usage relationship.

        a invocation relationship is the triggering of an activity by another activity.

        a usage relationship happens when an activity consumes an entity
        generated by another activity.

        Args:
            predicate (str): a predicate to match.

                a string in the form of: "field1"="valueA" or "field2"="valueB".

                possible fields are:

                - prov:role (string). bbp:value or bbp:document.
                - prov:value (string). a serialization of the value or the url.
                - bbp:ontologyname (string). a ontology identifier.

                example :

                "bbp:job"="44f8c20a-d518-11e3-ac11-0050569721c6"

            direction (str, optional): define if upstream and/or downstream provenance is retrieved.
                possible values are:

                - up: navigate through upstream relationships.
                - down: navigate through downstream relationships.
                - both: combine 'up' and 'down' expanded provenance data.

            depth (int, optional): define the number of relationships
                that will be dereferenced during expansion.

            relation (str, optional): define the relationship used.
                possible values are:

                - usage
                - invocation

            complete (str, optional): a set of path elements completing the matched activities.
                a comma separated list of path elements.

                a path element can be in:

                - usingActivity
                - usedEntity
                - generatedEntity
                - generatingActivity
                - derivatingEntity
                - derivatedEntity
                - derivatedFromEntity
                - derivatedToEntity
                - derivatedFromActivity
                - derivatedByActivity
                - triggeredEntity
                - triggeringEntity
                - startingActivity
                - startedActivity
                - triggeringActivity
                - triggeredActivity
                - activityResponsible
                - activityDelegated
                - delegatedForActivity
                - responsible
                - responsibleForActivity
                - delegated
                - associatedActivity
                - associatedAgent

        Returns:
            a prov-json serialization of the matching activities.

            the complete schema is defined in
            http://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
            '''
        query_fields = Client._get_expand_fields(predicate,
                                                 direction, depth, relation, complete)
        prov_json = self._activity.get_activity_expand(**query_fields)
        return prov_json

    @sh.swagger_error
    def expand_entities(self, predicate, direction='both',
                        depth=1, relation='usage', complete=None):
        ''' retrieve a set of entities matching predicate and expand it following a relation.

        retrieve a set of entities as defined in
        http://www.w3.org/TR/2013/REC-prov-dm-20130430/#term-entity
        matching a predicate and returns a prov-json serialization of it .

        expand the list of activities by navigating to next activity
        following a derivation relationship or a usage relationship.

        a derivation relationship happens when an entity is build based on a pre-existing entity.

        a usage relationship happens when an entity is consumed an activity
        and produced another entity.

        Args:
            predicate (str): a predicate to match.

                a string in the form of: "field1"="valueA" or "field2"="valueB".

                possible fields are:

                - prov:role (string). bbp:value or bbp:document.
                - prov:value (string). a serialization of the value or the url.
                - bbp:ontologyname (string). a ontology identifier.

                example :

                "bbp:job"="44f8c20a-d518-11e3-ac11-0050569721c6"

            direction (str, optional): define if upstream and/or downstream provenance is retrieved.
                possible values are:

                - up: navigate through upstream relationships.
                - down: navigate through downstream relationships.
                - both: combine 'up' and 'down' expanded provenance data.

            depth (int, optional): define the number of relationships
                that will be dereferenced during expansion.

            relation (str, optional): define the relationship used.
                possible values are:

                - usage
                - derivation

            complete (str, optional): a set of path elements completing the matched activities.
                a comma separated list of path elements.

                a path element can be in:

                - usingActivity
                - usedEntity
                - generatedEntity
                - generatingActivity
                - derivatingEntity
                - derivatedEntity
                - derivatedFromEntity
                - derivatedToEntity
                - derivatedFromActivity
                - derivatedByActivity
                - triggeredEntity
                - triggeringEntity
                - startingActivity
                - startedActivity
                - triggeringActivity
                - triggeredActivity
                - activityResponsible
                - activityDelegated
                - delegatedForActivity
                - responsible
                - responsibleForActivity
                - delegated
                - associatedActivity
                - associatedAgent

        Returns:
            a prov-json serialization of the matching entities.

            the complete schema is defined in
            http://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
            '''
        query_fields = Client._get_expand_fields(predicate,
                                                 direction, depth, relation, complete)
        prov_json = self._entity.get_entity_expand(**query_fields)
        return prov_json

    def get_job_returns(self, job_id):
        ''' retrieve the returned values of a finished job as a dictionary where the keys
        are the names (might have been automatically generated as return_0, return_1..) and the
        values are the results'''
        prov_data = self.get_activities(
            predicate='"bbp:jobId"="%s"' % job_id,
            path='generatedEntity[relation."bbp:scope"="bbp:parameter"]')
        L.debug('prov data: %s', prov_data)

        results = dict((k['prov:role'],
                        prov_data['entity'][k['prov:entity']]['prov:value'])
                       for k in prov_data['wasGeneratedBy'].values())

        L.debug('generated values: %s', results)
        return results

    def get_job_documents(self, job_id):
        '''retrieve the uuids of all of the generated documents of a finished job'''
        prov_data = self.get_activities(
            predicate='"bbp:jobId"="%s"' % job_id,
            path='generatedEntity[relation."bbp:scope"="bbp:document"]')
        L.debug('prov data: %s', prov_data)

        documents = dict((k['prov:role'],
                          prov_data['entity'][k['prov:entity']]['prov:value'])
                         for k in prov_data['wasGeneratedBy'].values())

        L.debug('generated documents: %s', documents)
        return documents

    def get_job_log(self, job_id):
        '''retrieve the uuids of the job log generated by a finished job'''
        return self.get_job_documents(job_id)['bbp:jobLog']

    def post_prov_dm(self, prov_dm_json):
        '''post Prov-DM to operation REST endpoint'''
        url = joinp(self.host, 'operation')
        resp = requests.post(url, json=prov_dm_json, headers=self._get_headers())
        L.debug('Provenance service POST /operation call took: %s', resp.elapsed)
        if resp.status_code != 200:
            raise ProvException('Failed to send prov_dm %s\n%s' % (resp.status_code, resp.text))

    def attribute(self, agent, entity):
        '''register attribution relation between agent and entity

        http://www.w3.org/TR/prov-dm/#term-attribution
        '''
        PROV_AGENT = 'prov:agent'
        PROV_ENTITY = 'prov:entity'
        AGENT = 'agent'
        ENTITY = 'entity'
        WAS_ATTRIBUTED_TO = 'wasAttributedTo'

        prov_dm = collections.defaultdict(dict)
        prov_dm[AGENT]['a0'] = agent
        prov_dm[ENTITY]['e0'] = entity

        prov_dm[WAS_ATTRIBUTED_TO]['wat0'] = {PROV_AGENT: 'a0', PROV_ENTITY: 'e0'}

        self.post_prov_dm(prov_dm)

    def document_uploaded(self, sciper, doc_uuid):
        '''register provenance when document was uploaded

        Args:
            sciper(str): sciper id of user who uploaded the document
            doc_uuid(str): document uuid
        '''
        PROV_TYPE = 'prov:type'
        PROV_VALUE = 'prov:value'
        PROV_ROLE = "prov:role"
        PROV_PERSON = 'prov:person'
        BBP_VALUE = 'bbp:value'
        BBP_AUTH_TYPE = 'bbp:authType'
        BBP_GASPAR = 'bbp:gaspar'
        BBP_DOCUMENT = 'bbp:document'

        agent = {BBP_VALUE: sciper, PROV_TYPE: PROV_PERSON, BBP_AUTH_TYPE: BBP_GASPAR}
        entity = {PROV_ROLE: BBP_DOCUMENT, PROV_VALUE: doc_uuid}
        self.attribute(agent, entity)
