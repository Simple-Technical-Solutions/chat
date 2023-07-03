import { useEffect, useState } from 'react';
import CodeAreaModal from '../codeAreaModal';

export default function CodeAreaComponent({ value, onChange, disabled, editNode = false }: any) {
  const [myValue, setMyValue] = useState(typeof value == 'string' ? value : JSON.stringify(value));
  const [openPopUp, setOpenPopUp] = useState(false);

  useEffect(() => {
    if (disabled) {
      setMyValue('');
      onChange('');
    }
  }, [disabled, onChange]);

  useEffect(() => {
    setMyValue(typeof value == 'string' ? value : JSON.stringify(value));
  }, [value]);

  return (
    <div className={disabled ? 'pointer-events-none w-full cursor-not-allowed' : 'w-full'}>
      {openPopUp ? (
        <CodeAreaModal
          value={myValue}
          setValue={(t: string) => {
            setMyValue(t);
            onChange(t);
          }}
          onClose={() => {
            setOpenPopUp(false);
          }}
        />
      ) : null}
      <div className="flex w-full items-center">
        <span
          onClick={() => {
            setOpenPopUp(true);
          }}
          className={
            editNode
              ? 'form-input block w-full cursor-pointer truncate rounded-md border border-ring bg-transparent pb-0.5 pt-0.5 text-sm text-ring shadow-sm placeholder:text-center sm:text-sm'
              : 'block w-full truncate rounded-md border border-ring px-3 py-2 text-ring shadow-sm placeholder:text-muted-foreground sm:text-sm' +
                (disabled ? ' bg-input' : '')
          }
        >
          {myValue !== '' ? myValue : 'Type something...'}
        </span>
        <button
          onClick={() => {
            setOpenPopUp(true);
          }}
        >
          {!editNode && (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-6 h-6 hover:text-ring dark:text-gray-300 ml-3"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" x2="21" y1="14" y2="3"></line>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
