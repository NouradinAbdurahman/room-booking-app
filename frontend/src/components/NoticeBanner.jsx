import { AlertIcon, CheckIcon } from "./Icons.jsx";

/** A green success or red error banner for a { kind, text } notice; errors are announced as alerts. */
export default function NoticeBanner({ notice }) {
  if (!notice) return null;
  const isError = notice.kind === "error";
  return (
    <div className={`banner banner--${notice.kind}`} role={isError ? "alert" : "status"}>
      {isError ? <AlertIcon /> : <CheckIcon />} {notice.text}
    </div>
  );
}
