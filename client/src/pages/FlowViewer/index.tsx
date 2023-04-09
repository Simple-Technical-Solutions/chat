import { Button } from "@mui/material";
import { useState, useRef, useCallback, useEffect } from "react";
import { useLocation, useParams } from "react-router-dom";
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Connection,
  Edge,
  ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { ChainFuryNode } from "../../components/ChainFuryNode";
import { useAuthStates } from "../../redux/hooks/dispatchHooks";
import { useAppDispatch } from "../../redux/hooks/store";
import {
  useComponentsMutation,
  useCreateBotMutation,
  useEditBotMutation,
} from "../../redux/services/auth";
import { setComponents } from "../../redux/slices/authSlice";

export const nodeTypes = { ChainFuryNode: ChainFuryNode };

const FlowViewer = () => {
  const reactFlowWrapper = useRef(null) as any;
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true as boolean);
  const [reactFlowInstance, setReactFlowInstance] = useState(
    null as null | ReactFlowInstance
  );
  const [variant, setVariant] = useState("" as "new" | "edit");
  const { flow_id } = useParams() as {
    flow_id: string;
  };
  const [botName, setBotName] = useState("" as string);
  const [getComponents] = useComponentsMutation();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const [createBot] = useCreateBotMutation();
  const [editBot] = useEditBotMutation();
  const { auth } = useAuthStates();

  useEffect(() => {
    if (location.search?.includes("?bot=") && flow_id === "new") {
      setBotName(location.search.split("?bot=")[1]);
      setVariant("new");
      setNodes([]);
      setEdges([]);
      setLoading(false);
    } else {
      setVariant("edit");
    }
    fetchComponents();
  }, [location]);

  useEffect(() => {
    if (auth?.chatBots?.[flow_id]) {
      setLoading(false);
      createNodesForExistingBot();
    }
  }, [auth.chatBots, location]);

  const fetchComponents = async () => {
    getComponents()
      .unwrap()
      .then((res) => {
        dispatch(
          setComponents({
            components: res,
          })
        );
      })
      ?.catch(() => {
        alert("Error fetching components");
      });
  };

  const onConnect = useCallback(
    (params: Edge<any> | Connection) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  const onDragOver = useCallback(
    (event: {
      preventDefault: () => void;
      dataTransfer: { dropEffect: string };
    }) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    },
    []
  );

  const onDrop = useCallback(
    (event: {
      preventDefault: () => void;
      dataTransfer: { getData: (arg0: string) => any };
      clientX: number;
      clientY: number;
    }) => {
      event.preventDefault();
      if (reactFlowInstance?.project && reactFlowWrapper?.current) {
        const reactFlowBounds =
          reactFlowWrapper?.current?.getBoundingClientRect();
        let type = event.dataTransfer.getData("application/reactflow");
        const nodeData = JSON.parse(type);
        type = nodeData?.displayName;
        console.log({ nodeData, type });
        // check if the dropped element is valid
        if (typeof type === "undefined" || !type) {
          return;
        }

        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });
        const newNode = {
          id: type,
          position,
          type: "ChainFuryNode",
          data: {
            node: nodeData,
            id: type,
            value: null,
            deleteMe: () => {
              setNodes((nds) => nds.filter((node) => node.id !== type));
            },
          },
        };

        setNodes((nds) => nds.concat(newNode));
      }
    },
    [reactFlowInstance]
  );

  const createChatBot = () => {
    createBot({ name: botName, nodes, edges, token: auth?.accessToken })
      .unwrap()
      ?.then((res) => {
        console.log(res);
        alert("Bot created successfully");
      })
      .catch((err) => {
        console.log(err);
        alert("Error creating bot");
      });
  };

  const createNodesForExistingBot = () => {
    auth.chatBots?.[flow_id]?.dag?.nodes?.forEach((node: any) => {
      const newNode = {
        id: node?.id ?? "",
        position: node?.position ?? { x: 0, y: 0 },
        type: "ChainFuryNode",
        data: {
          ...node?.data,
          node: JSON.parse(JSON.stringify(node?.data?.node)),
          deleteMe: () => {
            setNodes((nds) => nds.filter((delnode) => delnode.id !== node?.id));
          },
        },
      };
      setNodes((nds) => nds.concat(newNode));
    });
    setEdges(auth.chatBots?.[flow_id]?.dag?.edges);
  };

  const editChatBot = () => {
    editBot({
      id: flow_id,
      name: auth?.chatBots?.[flow_id]?.name,
      nodes,
      edges,
      token: auth?.accessToken,
    })
      .unwrap()
      ?.then((res) => {
        console.log({ hh: reactFlowInstance?.getNodes() });
        alert("Bot edited successfully");
      })
      .catch((err) => {
        console.log(err);
        alert("Error editing bot");
      });
  };

  return (
    <div className=" w-full max-h-screen flex flex-col overflow-hidden prose-nbx">
      <div className="p-[16px] border-b border-light-neutral-grey-200 semiBold350">
        {variant === "new"
          ? "Start building your flow by dragging and dropping nodes from the left panel"
          : "Edit your flow by dragging and dropping nodes from the left panel"}
        <Button
          className="h-[28px]"
          variant="outlined"
          color="primary"
          onClick={() => {
            if (variant === "new") {
              createChatBot();
            } else {
              editChatBot();
            }
          }}
          sx={{ float: "right" }}
        >
          {variant === "new" ? "Create" : "Save"}
        </Button>
      </div>
      {!loading ? (
        <ReactFlowProvider>
          <div className=" w-[calc(100vw-250px)] h-full" ref={reactFlowWrapper}>
            <ReactFlow
              nodeTypes={nodeTypes}
              proOptions={{ hideAttribution: true }}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onInit={setReactFlowInstance}
              onDrop={onDrop}
              onDragOver={onDragOver}
              fitView={true}
              defaultViewport={{
                zoom: 0.8,
                y: 0,
                x: 0,
              }}
            >
              <Controls />
            </ReactFlow>
          </div>
        </ReactFlowProvider>
      ) : (
        ""
      )}
    </div>
  );
};

export default FlowViewer;