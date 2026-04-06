export default function ResultsHeader({
  fileName,
  onEditInputs,
}: {
  fileName: string;
  onEditInputs: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
          Analysis complete
        </p>
        <h1 className="mt-1 text-3xl font-bold">Your ATS results</h1>
        <p className="mt-2 text-sm text-slate-600">
          Resume: <span className="font-medium">{fileName}</span>
        </p>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onEditInputs}
          className="rounded-2xl border border-slate-300 px-4 py-2.5 font-medium text-slate-700 transition hover:bg-slate-50"
        >
          Edit inputs
        </button>
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="rounded-2xl bg-slate-900 px-4 py-2.5 font-medium text-white transition hover:bg-slate-800"
        >
          Back to top
        </button>
      </div>
    </div>
  );
}
