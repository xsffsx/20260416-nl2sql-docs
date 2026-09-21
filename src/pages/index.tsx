import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from '@site/src/css/home.module.css';

const features = [
  ['Knowledge-grounded', 'RAG, semantic mappings, and few-shot examples stay visible as part of the SQL generation contract.'],
  ['Runtime-verifiable', 'Startup readiness, QA Smoke, artifact snapshots, and Kubernetes operations are documented together.'],
  ['Source-oriented', 'Architecture decisions, APIs, diagrams, and troubleshooting guides live beside the project source.'],
];

function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();

  return (
    <Layout title="Knowledge-grounded NL2SQL" description={siteConfig.tagline}>
      <header className={clsx('hero hero--primary', styles.heroBanner)}>
        <div className="container">
          <Heading as="h1" className="hero__title">Knowledge-grounded NL2SQL</Heading>
          <p className={clsx('hero__subtitle', 'heroSubtitle')}>
            Understand the path from a business question to a verified SQL result.
          </p>
          <div>
            <Link className="button button--secondary button--lg" to="/docs/getting-started/overview">
              Get Started
            </Link>{' '}
            <Link className="button button--outline button--lg" to="/docs/architecture/langgraph-pipeline">
              View Architecture
            </Link>
          </div>
        </div>
      </header>
      <main>
        <section className="container margin-vert--xl">
          <div className="row">
            {features.map(([title, description]) => (
              <div className="col col--4 margin-bottom--lg" key={title}>
                <div className="featureCard">
                  <Heading as="h2" className="margin-bottom--sm">{title}</Heading>
                  <p>{description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}

export default Home;
