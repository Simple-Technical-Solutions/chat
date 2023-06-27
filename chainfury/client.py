import os
import requests
from functools import lru_cache
from typing import Dict, Any, Tuple

from chainfury.utils import logger
from chainfury.base import Chain, Node, Edge
from chainfury.agent import ai_actions_registry, programatic_actions_registry
from chainfury.types import Dag


class Subway:
    """
    Simple code that allows writing APIs by `.attr.ing` them. This is inspired from gRPC style functional calls which
    hides the complexity of underlying networking. This is useful when you are trying to debug live server directly.

    Note:
        User is solely responsible for checking if the certain API endpoint exists or not. This simply wraps the API
        calls and does not do any validation.

    Example:
        >>> from chainfury.client import Subway
        >>> from requests import Session
        >>> session = Session()
        >>> session.headers.update({"token": token})
        >>> stub = Subway.from_openapi("http://localhost:8000", session)
        >>> get_chain = stub.chatbot.u("6ln9ksln")       # u is a special method to access attributes that start with a number
        >>> chain = get_chain()                          # call like a function
        ... {'name': 'funny-bot-1',
            'description': None,
            'dag': {'nodes': [
                {'id': 'bc1bdc37-07d9-49b4-9e09-b0e58a535da5_934.2328674347034',
                 'cf_id': 'bc1bdc37-07d9-49b4-9e09-b0e58a535da5',
                 'position': {'x': -271.25233176301117, 'y': 78.20693852768798},
                 'type': 'FuryEngineNode',
                 'width': 350,
                 'height': 553,
                 'selected': True,
                 'position_absolute': None,
                 'dragging': False,
                 'data': {}
                }
            ],
            'edges': [],
            'sample': {'bc1bdc37-07d9-49b4-9e09-b0e58a535da5_934.2328674347034/model': 'gpt-3.5-turbo'},
            'main_in': 'bc1bdc37-07d9-49b4-9e09-b0e58a535da5_934.2328674347034/animal',
            'main_out': 'bc1bdc37-07d9-49b4-9e09-b0e58a535da5_934.2328674347034/text'},
            'engine': 'fury',
            'deleted_at': None,
            'created_by': 'cihua4hh',
            'id': 'l6lnksln',
            'meta': None,
            'created_at': '2023-06-27T18:05:17.395260'}

    Args:
        _url (str): The url to use for the client
        _session (requests.Session): The session to use for the client
    """

    def __init__(self, _url, _session):
        self._url = _url.rstrip("/")
        self._session = _session

    def __repr__(self):
        return f"<Subway ({self._url})>"

    def __getattr__(self, attr: str):
        # https://stackoverflow.com/questions/3278077/difference-between-getattr-vs-getattribute
        return Subway(f"{self._url}/{attr}", self._session)

    def u(self, attr: str) -> "Subway":
        """In cases where the api might start with a number you cannot write in python, this method can be used to
        access the attribute.

        Example:
            >>> stub.9jisjfi      # python will cry, invalid syntax: cannot start with a number
            >>> stub.u('9jisjfi') # do this instead

        Args:
            attr (str): The attribute to access

        Returns:
            Subway: The new subway object
        """
        return getattr(self, attr)

    def __call__(
        self,
        method="get",
        trailing="",
        json={},
        data=None,
        params: Dict = {},
        _verbose=False,
        **kwargs,
    ) -> Tuple[Dict[str, Any], bool]:
        """Call the API endpoint as if it is a function.

        Args:
            method (str, optional): The method to use. Defaults to "get".
            trailing (str, optional): The trailing url to use. Defaults to "".
            json (Dict[str, Any], optional): The json to use. Defaults to {}.
            data ([type], optional): The data to use. Defaults to None.
            params (Dict, optional): The params to use. Defaults to {}.
            _verbose (bool, optional): Whether to print the response or not. Defaults to False.

        Returns:
            Tuple[Dict[str, Any], bool]: The response and whether there was an error or not
        """
        fn = getattr(self._session, method)
        url = f"{self._url}{trailing}"
        if _verbose:
            logger.info(f"Calling {url}")
        items = {}
        if json:
            items["json"] = json
        if data:
            items["data"] = data
        if params:
            items["params"] = params
        r = fn(url, **items, **kwargs)
        if _verbose:
            logger.info(r.content.decode())
        try:
            r.raise_for_status()  # good when server is good
            return r.json(), False
        except:
            return r.content.decode(), True


@lru_cache(maxsize=1)
def get_client(prefix: str = "api/v1", url="", token: str = "") -> Subway:
    """This function returns a Subway object that can be used to interact with the API.

    Example:
        >>> from chainfury import get_client
        >>> client = get_client()
        >>> cf_actions = client.api.v1.fury.actions.list()
        >>> cf_actions

    Note:
        The `get_client` function is a convenience function that can be used to get a client object. It is not required
        to use the library. Under the hood, it still will call the chainfury REST endpoints.

    Args:
        prefix (str, optional): The prefix to use for the client. Defaults to "api/v1".
        url (str, optional): The url to use for the client or picks from `CF_URL` env var. Defaults to "".
        token (str, optional): The token to use for the client or picks from `CF_TOKEN` env var. Defaults to "".

    Raises:
        ValueError: If no url or token is provided.

    Returns:
        Subway: A Subway object that can be used to interact with the API.
    """
    url = url or os.environ.get("CF_URL", "")
    if not url:
        raise ValueError("No url provided, please set CF_URL environment variable or pass url as argument")
    token = token or os.environ.get("CF_TOKEN", "")
    if not token:
        raise ValueError("No token provided, please set CF_TOKEN environment variable or pass token as argument")

    session = requests.Session()
    session.headers.update({"token": token})
    sub = Subway(url, session)
    for p in prefix.split("/"):
        sub = getattr(sub, p)
    return sub


def get_chain_from_id(id: str) -> Chain:
    """Helper function to load a chain from the given chatbot ID. This assumed that everything was created correctly

    Example:
        >>> from chainfury.client import get_chain_from_id
        >>> chain = get_chain_from_id("l6lnksln")
        >>> chain

    Args:
        id (str): The id of the chain to load

    Returns:
        Chain: The chain object
    """
    # first we call the API to get the chains
    stub = get_client()
    chain, err = stub.chatbot.u(id)()
    if err:
        raise ValueError(f"Could not get chain with id {id}: {chain}")

    # convert to dag and checks
    nodes = []
    edges = []

    # convert to dag and checks
    dag = Dag(**chain["dag"])
    if not dag.sample:
        raise ValueError("Dag has no sample")
    if not dag.main_in:
        raise ValueError("Dag has no main_in")
    if not dag.main_out:
        raise ValueError("Dag has no main_out")

    # get all the actions by querying the APIs
    dag_nodes = dag.nodes
    actions_map = {}  # this is the map between the cf_id and the node object
    for node in dag_nodes:
        if not node.cf_id and not node.cf_data:
            raise ValueError(f"Action {node.id} has no cf_id or cf_data")
        if node.cf_data:
            cf_action = Node.from_dict(node.cf_data)
        else:
            cf_action = actions_map.get(node.cf_id, None)

        # check if this action is in the registry
        if not cf_action:
            # check if present in the AI registry
            try:
                # print("ai_actions_registry")
                cf_action = ai_actions_registry.get(node.cf_id)
            except ValueError:
                pass
        if not cf_action:
            # check if present in the programatic registry
            try:
                # print("programatic_actions_registry")
                cf_action = programatic_actions_registry.get(node.cf_id)
            except ValueError:
                pass
        if not cf_action:
            # check available on the API
            try:
                # print("stub.fury.actions.u(node.cf_id)()")
                action, err = stub.fury.actions.u(node.cf_id)()
                if err:
                    raise ValueError(f"Action {node.cf_id} not loaded: {action}")
                cf_action = Node.from_dict(action)
                actions_map[node.cf_id] = cf_action  # cache it
            except:
                raise ValueError(f"Action {node.cf_id} not found")

        # standardsize everything to node
        if not isinstance(cf_action, Node):
            cf_action = Node.from_dict(cf_action)
        cf_action.id = node.id  # override the id
        nodes.append(cf_action)
    # print(nodes)

    # now create all the edges
    dag_edges = dag.edges
    for edge in dag_edges:
        if not (edge.source and edge.target and edge.sourceHandle and edge.targetHandle):
            raise ValueError(f"Invalid edge {edge}")
        edges.append(Edge.from_dict(edge.dict()))

    out = Chain(
        nodes=nodes,
        edges=edges,
        sample=dag.sample,
        main_in=dag.main_in,
        main_out=dag.main_out,
    )
    return out


def create_new_chain(name: str, chain: Chain, create_actions: bool = False) -> Dict[str, Any]:
    """
    Creates a new chain with the given name and chain. If create_actions is True, it will also create the actions
    on the API.

    Example:
        >>> from chainfury import Chain
        >>> from chainfury.client import create_new_chain
        >>> api_resp = create_new_chain("my chain", chain)
        >>> chain_new = Chain.from_dict(api_resp)
        >>> chain_new

    Args:
        name (str): The name of the chain
        chain (Chain): The chain object
        create_actions (bool, optional): Whether to create the actions or not. Defaults to False.

    Returns:
        Dict[str, Any]: The API response
    """
    stub = get_client()
    chain_dict = chain.to_dict()
    nodes = chain_dict["nodes"]
    dag_nodes = []
    for i, node in enumerate(nodes):
        _node_data = {
            "id": node["id"],
            "position": {"x": i * 100, "y": i * 100},
            "type": "FuryEngineNode",
            "width": 100,
            "height": 100,
            "selected": False,
            "positionAbsolute": {
                "x": i * 100,
                "y": i * 100,
            },
            "dragging": False,
        }

        if create_actions:
            # in this case call the API and store the actions in which case the DAG only knows about the `cf_id`
            out, err = stub.fury.actions(
                "post",
                trailing="/",
                json={
                    "name": node["name"],
                    "description": "",
                    "fn": {
                        "model_id": node["fn"]["model"]["id"],
                        "model_params": node["fn"]["model_params"],
                        "fn": node["fn"]["fn"],
                    },
                    "outputs": node["outputs"],
                },
            )
            if err:
                raise ValueError(f"Could not create node: {out}")
            logger.info(f"Created new action with ID: {out['id']}")
            _node_data["cf_id"] = out["id"]
        else:
            # in this case the entire action is stored with the DAG object
            _node_data["cf_data"] = node

        # add the node to the list
        dag_nodes.append(_node_data)

    # update the chain_dict
    chain_dict["nodes"] = dag_nodes
    for e in chain_dict["edges"]:
        e["id"] = f"{e['source']}/{e['sourceHandle']}-{e['target']}{e['targetHandle']}"
    data = {"name": name, "dag": chain_dict, "engine": "fury"}
    out, err = stub.chatbot("post", trailing="/", json=data)
    if err:
        raise ValueError(f"Could not create chain: {out}")
    return out
