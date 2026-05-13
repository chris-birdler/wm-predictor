import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { Prediction } from "../types";

interface PredictionsCtx {
  predictions: Record<number, Prediction>;
  mergePredictions: (preds: Prediction[]) => void;
  resetPredictions: () => void;
}

const Ctx = createContext<PredictionsCtx | null>(null);

export function PredictionsProvider({ children }: { children: ReactNode }) {
  const [predictions, setPredictions] = useState<Record<number, Prediction>>({});

  const mergePredictions = useCallback((preds: Prediction[]) => {
    setPredictions((prev) => {
      const next = { ...prev };
      for (const p of preds) next[p.match_id] = p;
      return next;
    });
  }, []);

  const resetPredictions = useCallback(() => setPredictions({}), []);

  return (
    <Ctx.Provider value={{ predictions, mergePredictions, resetPredictions }}>
      {children}
    </Ctx.Provider>
  );
}

export function usePredictions(): PredictionsCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("usePredictions must be used inside PredictionsProvider");
  return v;
}
