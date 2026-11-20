import Editor, { loader, type EditorProps } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api';
import 'monaco-editor/language/json/monaco.contribution';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';
import JsonWorker from 'monaco-editor/language/json/json.worker?worker';
(
  globalThis as typeof globalThis & {
    MonacoEnvironment?: { getWorker: (_moduleId: string, label: string) => Worker };
  }
).MonacoEnvironment = {
  getWorker: (_moduleId, label) => (label === 'json' ? new JsonWorker() : new EditorWorker()),
};
monaco.languages.register({ id: 'markdown' });
monaco.languages.setMonarchTokensProvider('markdown', {
  tokenizer: {
    root: [
      [/^#{1,6} .*/, 'keyword'],
      [/^> .*/, 'comment'],
      [/`[^`]+`/, 'string'],
      [/\*\*[^*]+\*\*/, 'strong'],
    ],
  },
});
monaco.languages.register({ id: 'python' });
monaco.languages.setMonarchTokensProvider('python', {
  tokenizer: {
    root: [
      [/#.*$/, 'comment'],
      [
        /\b(?:import|from|def|class|return|if|elif|else|for|while|in|try|except|with|as|None|True|False|and|or|not)\b/,
        'keyword',
      ],
      [/"[^"\n]*"|'[^'\n]*'/, 'string'],
      [/\b\d+(?:\.\d+)?\b/, 'number'],
    ],
  },
});
loader.config({ monaco });
export default function LocalEditor(props: EditorProps) {
  return <Editor {...props} />;
}
