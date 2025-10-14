import { FormEvent, useEffect, useMemo, useState } from 'react';
import { fetchHealth, submitGeneration, type GeneratePayload } from './api';

const DEFAULT_NEGATIVE_PROMPT = 'low quality, artifacts, blurry';

type GenerationState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'error'; message: string }
  | { status: 'success'; response: unknown };

function useWanDefaults() {
  return useMemo(
    () => ({
      prompt: 'A cinematic establishing shot of a futuristic city at dusk',
      negativePrompt: DEFAULT_NEGATIVE_PROMPT,
      numFrames: 16
    }),
    []
  );
}

export default function App() {
  const wanDefaults = useWanDefaults();
  const [prompt, setPrompt] = useState<string>(wanDefaults.prompt);
  const [negativePrompt, setNegativePrompt] = useState<string>(wanDefaults.negativePrompt);
  const [numFrames, setNumFrames] = useState<number>(wanDefaults.numFrames);
  const [seed, setSeed] = useState<number | ''>('');
  const [health, setHealth] = useState<string>('Checking backend...');
  const [state, setState] = useState<GenerationState>({ status: 'idle' });

  useEffect(() => {
    let mounted = true;
    fetchHealth()
      .then((value) => {
        if (mounted) {
          setHealth(`Backend reachable: ${value}`);
        }
      })
      .catch((error) => {
        if (mounted) {
          setHealth(`Unable to reach backend: ${error instanceof Error ? error.message : String(error)}`);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: GeneratePayload = {
      prompt,
      negativePrompt: negativePrompt || undefined,
      numFrames,
      seed: typeof seed === 'number' ? seed : undefined
    };

    try {
      setState({ status: 'submitting' });
      const response = await submitGeneration(payload);
      setState({ status: 'success', response });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setState({ status: 'error', message });
    }
  }

  return (
    <main>
      <h1>Wan2 Inference Console</h1>
      <p>{health}</p>

      <section>
        <form onSubmit={handleSubmit}>
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            name="prompt"
            rows={4}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe the video you want Wan2 to create"
            required
          />

          <label htmlFor="negativePrompt">Negative Prompt</label>
          <textarea
            id="negativePrompt"
            name="negativePrompt"
            rows={2}
            value={negativePrompt}
            onChange={(event) => setNegativePrompt(event.target.value)}
            placeholder="Terms to avoid"
          />

          <label htmlFor="numFrames">Frames</label>
          <input
            id="numFrames"
            name="numFrames"
            type="number"
            min={1}
            max={256}
            value={numFrames}
            onChange={(event) => setNumFrames(Number(event.target.value) || wanDefaults.numFrames)}
          />

          <label htmlFor="seed">Seed (optional)</label>
          <input
            id="seed"
            name="seed"
            type="number"
            placeholder="Random seed"
            value={seed}
            onChange={(event) => {
              const value = event.target.value;
              setSeed(value === '' ? '' : Number(value));
            }}
          />

          <button type="submit" disabled={state.status === 'submitting'}>
            {state.status === 'submitting' ? 'Submitting…' : 'Generate'}
          </button>
        </form>

        <div className="output">
          {state.status === 'idle' && <p>Responses will appear here once you call the API.</p>}
          {state.status === 'submitting' && <p>Submitting prompt to the backend…</p>}
          {state.status === 'error' && <p>Error: {state.message}</p>}
          {state.status === 'success' && (
            <>
              <h2>Backend Response</h2>
              <pre>{JSON.stringify(state.response, null, 2)}</pre>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
