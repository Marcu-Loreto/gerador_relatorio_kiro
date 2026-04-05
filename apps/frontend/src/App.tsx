import { useState } from "react";

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Gerador de Relatórios Kiro
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
            Sistema profissional de análise documental e geração de relatórios
            com IA
          </p>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 max-w-2xl mx-auto">
            <h2 className="text-2xl font-semibold mb-4 text-gray-800 dark:text-white">
              Em Desenvolvimento
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              A interface completa está sendo desenvolvida. Por enquanto, você
              pode acessar a API em:
            </p>
            <a
              href="/docs"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Acessar Documentação da API
            </a>

            <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setCount((count) => count + 1)}
                className="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white font-medium py-2 px-4 rounded transition-colors"
              >
                Contador: {count}
              </button>
            </div>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <h3 className="font-semibold text-lg mb-2 text-gray-800 dark:text-white">
                6 Tipos de Relatórios
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Técnico, FINEP, Científico, Acadêmico e mais
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <h3 className="font-semibold text-lg mb-2 text-gray-800 dark:text-white">
                IA Multiagente
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Agentes especializados com LangGraph
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <h3 className="font-semibold text-lg mb-2 text-gray-800 dark:text-white">
                Segurança Robusta
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Proteção contra prompt injection
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
