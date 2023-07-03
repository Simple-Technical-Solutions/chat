import { useRef, useState } from 'react';
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-python';
import 'ace-builds/src-noconflict/theme-github';
import 'ace-builds/src-noconflict/theme-twilight';
import 'ace-builds/src-noconflict/ext-language_tools';
import { Dialog } from '@mui/material';
import SvgClose from '../SvgComps/Close';

export default function CodeAreaModal({
  value,
  setValue,
  onClose
}: {
  setValue: (value: string) => void;
  value: string;
  onClose: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [code, setCode] = useState(value);
  function setModalOpen(x: boolean) {
    setOpen(x);
    if (x === false) {
      setTimeout(() => {
        onClose();
      }, 300);
    }
  }
  return (
    <Dialog open={true} onClose={setModalOpen}>
      <div className="h-[500px] lg:max-w-[700px] overflow-hidden prose-nbx flex flex-col p-[16px]">
        <div className="mb-[4px]">
          <div className="flex items-center justify-between">
            <span className="semiBold300">Edit Code</span>
            <SvgClose
              className="stroke-dark-neutral-grey-600 cursor-pointer"
              onClick={() => {
                setModalOpen(false);
              }}
            />
          </div>
        </div>

        <AceEditor
          value={code}
          mode="python"
          highlightActiveLine={true}
          showPrintMargin={false}
          fontSize={14}
          showGutter
          enableLiveAutocompletion
          theme={'twilight'}
          name="CodeEditor"
          onChange={(value) => {
            setCode(value);
          }}
          className="h-[300px] w-full rounded-lg border-[1px] border-ring custom-scroll "
        />

        <div className="h-[50px] flex-1">
          <button
            className="mt-3 w-full p-[8px] bg-light-primary-blue-600 text-white rounded-md hover:bg-light-primary-blue-700"
            onClick={() => {
              setModalOpen(false);
              setValue(code);
            }}
            type="submit"
          >
            Check & Save
          </button>
        </div>
      </div>
    </Dialog>
  );
}
