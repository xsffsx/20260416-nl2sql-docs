import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'category',
      label: 'Getting Started',
      items: ['intro', 'getting-started/overview', 'getting-started/local-development'],
    },
    {
      type: 'category',
      label: 'Concepts',
      items: [
        'concepts/nl2sql-pipeline',
        'concepts/rag-few-shot',
        'concepts/semantic-key-value-mappings',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: ['architecture/langgraph-pipeline', 'architecture/mcp-integration'],
    },
    {
      type: 'category',
      label: 'Runtime Operations',
      items: [
        'runtime/startup-grace',
        'runtime/readiness-liveness',
        'runtime/qa-smoke',
        'runtime/artifact-snapshot',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: ['api/health-readiness', 'api/artifact-versions'],
    },
    {
      type: 'category',
      label: 'ADRs',
      items: ['adr/index', 'adr/runtime-boundaries'],
    },
    {
      type: 'category',
      label: 'Troubleshooting',
      items: ['troubleshooting/startup-blocked'],
    },
  ],
};

export default sidebars;
