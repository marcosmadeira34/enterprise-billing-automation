import React from "react";

export function App(): React.JSX.Element {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white">
          <span className="text-xl font-bold">EBA</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Enterprise Billing Automation
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Plataforma de faturamento corporativo para operações recorrentes de alta escala.
        </p>
        <div className="mt-6 rounded-lg bg-slate-50 p-4 text-xs font-mono text-slate-700">
          Ambiente Inicializado • Status: Operacional
        </div>
      </div>
    </div>
  );
}

export default App;

