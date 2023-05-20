"""
# Agent

This file contains methods and functions that are used to create an agent, i.e.
- model registry
- memory registry
- functional node registry
"""

import copy
import traceback
from functools import lru_cache
from typing import Any, List, Optional, Union, Dict, Tuple

import jinja2

from fury.base import (
    logger,
    func_to_vars,
    func_to_return_vars,
    jtype_to_vars,
    extract_jinja_indices,
    get_value_by_keys,
    put_value_by_keys,
    pyannotation_to_json_schema,
    Node,
    Model,
    ModelTags,
    Chain,
    Var,
)

"""
## Models

All the things below are for the models that are registered in the model registry, so that they can be used as inputs
in the chain. There can be several models that can put as inputs in a single chatbot.
"""


class ModelRegistry:
    tags_types = ModelTags

    def __init__(self):
        self.models: Dict[str, Model] = {}
        self.counter: Dict[str, int] = {}
        self.tags_to_models: Dict[str, List[str]] = {}

    def has(self, model_id: str):
        return model_id in self.models

    def register(
        self,
        fn: object,
        collection_name: str,
        model_id: str,
        description: str,
        tags: List[str] = [],
    ):
        id = f"{model_id}"
        logger.debug(f"Registering model {model_id} at {id}")
        if id in self.models:
            raise Exception(f"Model {model_id} already registered")
        self.models[id] = Model(
            collection_name=collection_name,
            model_id=model_id,
            fn=fn,
            description=description,
            vars=func_to_vars(fn),
            tags=tags,
        )
        for tag in tags:
            self.tags_to_models[tag] = self.tags_to_models.get(tag, []) + [id]

    def get_tags(self) -> List[str]:
        return list(self.tags_to_models.keys())

    def get_models(self, tag: str = "") -> List[Dict[str, Any]]:
        return [{k: v.to_dict()} for k, v in self.models.items()]

    def get(self, model_id: str) -> Optional[Model]:
        self.counter[model_id] = self.counter.get(model_id, 0) + 1
        out = self.models.get(model_id, None)
        if out is None:
            raise ValueError(f"Model {model_id} not found")
        return out

    def get_count_for_model(self, model_id: str) -> int:
        return self.counter.get(model_id, 0)


model_registry = ModelRegistry()


"""
## Programtic Actions Registry

Programtic actions are nodes that are software 1.0 nodes, i.e. they are not trainable. They are used for things like
calling an API, adding 2 numbers, etc. Since they are not trainable the only way to get those is the source code for
the server.
"""


class ProgramaticActionsRegistry:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.counter: Dict[str, int] = {}
        self.tags_to_nodes: Dict[str, List[str]] = {}

    def register(
        self,
        fn: object,
        node_id: str,
        description: str,
        returns: List[str] = [],
        outputs=None,
        tags: List[str] = [],
    ) -> Node:
        logger.debug(f"Registering p-node '{node_id}'")
        if node_id in self.nodes:
            raise Exception(f"Node '{node_id}' already registered")
        if not outputs:
            assert len(returns), "If outputs is not provided then returns must be provided"
            outputs = {x: () for x in returns}
        else:
            assert len(outputs), "If returns is not provided then outputs must be provided"
        ops = func_to_return_vars(func=fn, returns=outputs)
        self.nodes[node_id] = Node(
            id=node_id,
            type=Node.types.PROGRAMATIC,
            fn=fn,
            description=description,
            fields=func_to_vars(fn),
            outputs=ops,
        )
        for tag in tags:
            self.tags_to_nodes[tag] = self.tags_to_nodes.get(tag, []) + [node_id]
        return self.nodes[node_id]

    def get_tags(self) -> List[str]:
        return list(self.tags_to_nodes.keys())

    def get_nodes(self, tag: str = "") -> List[Dict[str, Any]]:
        return [{k: v.to_dict()} for k, v in self.nodes.items()]

    def get(self, node_id: str) -> Optional[Node]:
        self.counter[node_id] = self.counter.get(node_id, 0) + 1
        out = self.nodes.get(node_id, None)
        if out is None:
            raise ValueError(f"p-node '{node_id}' not found")
        return out

    def get_count_for_nodes(self, node_id: str) -> int:
        return self.counter.get(node_id, 0)


programatic_actions_registry = ProgramaticActionsRegistry()


"""
## AI Actions Registry

For everything that cannot be done by we have the AI powered actions Registry. This registry
will not include all the things that are available to the outer service, but those that are
hardcoded in the entire thing somewhere.
"""


class AIAction:
    JTYPE = "jinja-template"
    FUNC = "python-function"

    def __init__(self, node_id: str, model: Model, model_params: Dict[str, Any], fn: object, outputs: Dict[str, Any] = {}):
        # do some basic checks that we can do before anything else like checking if model_params
        # is a subset of the model.vars
        fields = set(x.name for x in model.vars)
        mp_set = set(model_params.keys())
        if not mp_set.issubset(fields):
            raise Exception(f"Model params {mp_set} not a subset of {fields}")

        self.templates = []

        # since this is the AI action this is responsible for validating the function
        if type(fn) == dict:
            action_source = AIAction.JTYPE
            fields = []  # fields required for self.fields
            templates = []  # list of all the templates to be render with its position in fn
            fields_with_locations = extract_jinja_indices(fn)
            for field in fields_with_locations:
                fields.extend(field[1])
                obj = get_value_by_keys(fn, field[0])
                if not obj:
                    raise ValueError(f"Field {field[0]} not found in {fn}, but was extraced. There is a bug in get_value_by_keys function")
                templates.append((obj, jinja2.Template(obj), field[0]))

            # set values
            self.templates = templates
        else:
            assert type(fn) == type(func_to_return_vars), "`fn` can either be a function or a string"
            action_source = AIAction.FUNC
            fields = func_to_vars(fn)

        self.node_id = node_id
        self.model = model
        self.model_params = model_params
        self.fn = fn
        self.action_source = action_source
        self.fields = fields
        self.outputs = outputs

    def __call__(self, **data: Dict[str, Any]) -> Tuple[Any, Optional[Exception]]:
        # check for keys even before calling any API or something
        # we need to create a sub dict that only contains the fields that are needed by the preprocessor
        # function and pass the rest of the data to the model call
        _data = {}
        for f in self.fields:
            if f.required and f.name not in data:
                raise Exception(f"Field {f.name} is required in {self.node_id} but not present")
            if f.name in data:
                _data[f.name] = data.pop(f.name)

        if self.action_source == AIAction.FUNC:
            try:
                fn_out = self.fn(**_data)  # type: ignore
                if self.action_source == AIAction.FUNC and not type(fn_out) == dict:
                    raise Exception(f"AI Action preprocessor for {self.node_id} did not return a dict but {type(fn_out)}")
            except Exception as e:
                return "", e
        elif self.action_source == AIAction.JTYPE:
            fn_out = copy.deepcopy(self.fn)
            for raw, t, keys in self.templates:
                value = t.render(**_data)
                put_value_by_keys(fn_out, keys, value)

        # print(">> model_params:", self.model_params)
        # print(">> preprocessor:", fn_out)
        model_final_params = {**self.model_params}
        model_final_params.update(data)
        model_final_params.update(fn_out)  # type: ignore
        out, err = self.model(model_final_params)
        if err != None:
            return "", err

        # if self.outputs:
        #     fout = {}
        #     for k, loc in self.outputs.items():
        #         fout[k] = get_value_by_keys(out, loc)
        #     fout["__raw__"] = out
        #     out = fout
        return out, err


class AIActionsRegistry:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.counter: Dict[str, int] = {}
        self.tags_to_nodes: Dict[str, List[str]] = {}

    def register(
        self,
        node_id: str,
        model_id: str,
        model_params: Dict[str, Any],
        fn: object,
        outputs: Dict[str, Any],
        description: str = "",
        tags: List[str] = [],
    ) -> Node:
        """

        Args:
            outputs: This is a dict like `{'x': (-1, 'b', 'c')}`, if provided function returns a dictionary with key `x`
              and value automatically extracted from the model output at location `(-1, 'b', 'c')`.
        """
        logger.debug(f"Registering ai-node '{node_id}'")
        model = model_registry.get(model_id)
        if model is None:
            raise Exception(f"Model {model_id} not found")
        ai_action = AIAction(
            node_id=node_id,
            model=model,
            model_params=model_params,
            fn=fn,
            outputs=outputs,
        )
        if not outputs:
            output_field = [
                func_to_return_vars(
                    func=ai_action.__call__,
                    returns={
                        "model_output": (),
                    },
                ),
            ]
        else:
            output_field = [Var(type="any", name=k, _loc=loc) for k, loc in outputs.items()]
        self.nodes[node_id] = Node(
            id=node_id,
            fn=ai_action,
            type=Node.types.AI,
            description=description,
            fields=ai_action.fields + model.vars,
            outputs=output_field,  # type: ignore
        )
        for tag in tags:
            self.tags_to_nodes[tag] = self.tags_to_nodes.get(tag, []) + [node_id]
        return self.nodes[node_id]

    def get_tags(self) -> List[str]:
        return list(self.tags_to_nodes.keys())

    def get_nodes(self, tag: str = "") -> List[Dict[str, Any]]:
        return [{k: v.to_dict()} for k, v in self.nodes.items()]

    def get(self, node_id: str) -> Optional[Node]:
        self.counter[node_id] = self.counter.get(node_id, 0) + 1
        out = self.nodes.get(node_id, None)
        if out is None:
            raise ValueError(f"ai-node '{node_id}' not found")
        return out

    def get_count_for_nodes(self, node_id: str) -> int:
        return self.counter.get(node_id, 0)


ai_actions_registry = AIActionsRegistry()

# class Memory:
#     def __init__(self, memory_id):
#         self.node = Node(id=f"cf-memory-{memory_id}", type=Node.types.MEMORY)

#     # user can subclass this and override the following functions
#     def get(self, key: str):
#         ...

#     def put(self, key: str, value: Any):
#         ...


# # the main class, user can either subclass this or prvide the chain
# class Agent:
#     def __init__(self, models: List[Model], chain: Chain):
#         self.models = models
#         self.chain = chain

#     def __call__(self, user_input: Any):
#         return self.chain(user_input)


# # we LRU cache this to save time on ser / deser
# @lru_cache(128)
# def get_agent(models: List[Model], chain: Chain) -> Agent:
#     return Agent(
#         models=models,
#         chain=chain,
#     )


if __name__ == "__main__":
    pass
