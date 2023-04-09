import { Button } from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuthStates } from "../redux/hooks/dispatchHooks";
import { useAppDispatch } from "../redux/hooks/store";
import { useGetBotsMutation } from "../redux/services/auth";
import { setChatBots, setSelectedChatBot } from "../redux/slices/authSlice";
import ChatBotCard from "./ChatBotCard";
import CollapsibleComponents from "./CollapsibleComponents";
import NewBotModel from "./NewBotModel";

const Sidebar = () => {
  const [newBotModel, setNewBotModel] = useState(false);
  const { flow_id } = useParams();
  const navigate = useNavigate();
  const { auth } = useAuthStates();
  const [getBots] = useGetBotsMutation();
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!localStorage.getItem("accessToken")) {
      navigate("/login");
    } else {
      getBotList();
    }
  }, []);

  const getBotList = () => {
    try {
      getBots({
        token: auth?.accessToken,
      })
        .unwrap()
        .then((res) => {
          dispatch(
            setChatBots({
              chatBots: res?.chatbots?.length ? res?.chatbots : [],
            })
          );
          dispatch(setSelectedChatBot({ chatBot: res?.chatbots[0] }));
        })
        .catch((err) => {
          console.log(err);
        });
    } catch (err) {
      console.log(err);
    }
  };

  const onDragStart = (
    event: {
      dataTransfer: {
        setData: (arg0: string, arg1: any) => void;
        effectAllowed: string;
      };
    },
    nodeType: any
  ) => {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="overflow-hidden w-[250px] min-w-[250px] border-r h-screen shadow-sm bg-light-system-bg-secondary p-[8px] prose-nbx">
      {newBotModel ? <NewBotModel onClose={() => setNewBotModel(false)} /> : ""}
      <Button
        onClick={() => setNewBotModel(true)}
        variant="contained"
        className="my-[8px!important]"
        color="primary"
        fullWidth
      >
        New Bot
      </Button>
      <div className="overflow-scroll max-h-[calc(100%-60px)]">
        {!flow_id ? (
          <>
            <div className="flex flex-col gap-[8px]">
              <span className="semiBold250 text-light-neutral-grey-900">
                Bots
              </span>
              {Object.values(auth?.chatBots ?? [])?.map((bot, key) => {
                return (
                  <div
                    onClick={() => {
                      dispatch(
                        setSelectedChatBot({
                          chatBot: bot,
                        })
                      );
                    }}
                  >
                    <ChatBotCard key={key} label={bot?.name} />
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="flex flex-col gap-[8px]">
            {Object.keys(auth?.components).map((bot, key) => {
              return (
                <CollapsibleComponents
                  key={key}
                  label={bot}
                  onDragStart={onDragStart}
                  values={auth?.components[bot]}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;