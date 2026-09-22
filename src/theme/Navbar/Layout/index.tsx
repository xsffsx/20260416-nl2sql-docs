import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import NavbarLayout from '@theme-original/Navbar/Layout';

const sections = [
  ['Documentation', '/docs/'],
  ['Admin', '/docs/runtime/readiness-liveness'],
  ['Embedding', '/docs/architecture/mcp-integration'],
  ['Reference', '/docs/api/health-readiness'],
  ['NL2SQL Core', '/docs/architecture/overview'],
  ['Recipes', '/docs/concepts/rag-few-shot'],
  ['API', '/docs/api/health-readiness'],
];

export default function NavbarLayoutWrapper(props: Record<string, unknown>): ReactNode {
  return (
    <>
      <NavbarLayout {...props} />
      <nav className="docsSectionNav" aria-label="Documentation sections">
        <div className="docsSectionNav__inner">
          {sections.map(([label, to]) => (
            <Link
              key={label}
              className={`docsSectionNav__link${label === 'NL2SQL Core' ? ' docsSectionNav__link--core' : ''}`}
              to={to}
            >
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
