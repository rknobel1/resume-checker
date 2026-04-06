import Spinner from "./Spinner";

export default function LoadingState({
  onEditInputs,
}: {
  onEditInputs: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center rounded-3xl border border-slate-200 bg-white px-6 py-16 text-center shadow-xl">
      <Spinner />
      <h2 className="mt-6 text-2xl font-semibold">Analyzing your resume</h2>
      <p className="mt-2 max-w-md text-slate-600">
        Matching your resume against the job description, checking gaps, and
        generating improvement priorities.
      </p>

      <div className="mt-8 w-full max-w-md">
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-slate-900" />
        </div>
      </div>

      <button
        type="button"
        onClick={onEditInputs}
        className="mt-8 rounded-2xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
      >
        Back to edit inputs
      </button>
    </div>
  );
}
