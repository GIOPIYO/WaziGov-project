const PROJECTS_URL = '/data/projects.json';

async function fetchProjects(url) {
  const response = await fetch(url, { cache: 'no-store' });

  if (!response.ok) {
    throw new Error(`Failed to load ${url} (${response.status})`);
  }

  return response.json();
}

export async function loadProjectSummaries() {
  return fetchProjects(PROJECTS_URL);
}

export { PROJECTS_URL };