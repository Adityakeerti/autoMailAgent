const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

const TOKEN_KEY = "getnewjob_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const removeToken = () => localStorage.removeItem(TOKEN_KEY);

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  options.credentials = "include";
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (!endpoint.startsWith("/auth/")) {
      removeToken();
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Request failed" }));
    let msg = "Request failed";
    if (typeof errorData.detail === "string") {
      msg = errorData.detail;
    } else if (Array.isArray(errorData.detail)) {
      msg = errorData.detail.map((e: any) => `${e.loc?.slice(-1)[0] || 'field'}: ${e.msg}`).join("; ");
    }
    throw new Error(msg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  signup: (data: any) => request<{ access_token: string }>("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data: any) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  googleAuth: (email: string) => request<{ access_token: string }>("/auth/google", { method: "POST", body: JSON.stringify({ email }) }),
  getGoogleAuthUrl: () => request<{ url: string }>("/auth/google/url"),

  // Settings
  getSettings: () => request<any>("/settings"),
  updateSettings: (data: any) => request<any>("/settings", { method: "PUT", body: JSON.stringify(data) }),

  // Resumes & Context
  uploadResume: (formData: FormData, mode: string = "keep_unique") => request<any>(`/resume/upload?mode=${mode}`, { method: "POST", body: formData }),
  listResumes: () => request<any[]>("/resume"),
  triggerParse: (id: number, mode: string = "keep_unique") => request<any>(`/resume/${id}/parse?mode=${mode}`, { method: "POST" }),
  deleteResume: (id: number) => request<any>(`/resume/${id}`, { method: "DELETE" }),

  getProfile: () => request<any>("/context/profile"),
  updateProfile: (data: any) => request<any>("/context/profile", { method: "PUT", body: JSON.stringify(data) }),

  listExperiences: () => request<any[]>("/context/experience"),
  createExperience: (data: any) => request<any>("/context/experience", { method: "POST", body: JSON.stringify(data) }),
  updateExperience: (id: number, data: any) => request<any>(`/context/experience/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteExperience: (id: number) => request<any>(`/context/experience/${id}`, { method: "DELETE" }),

  listProjects: () => request<any[]>("/context/projects"),
  createProject: (data: any) => request<any>("/context/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: number, data: any) => request<any>(`/context/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id: number) => request<any>(`/context/projects/${id}`, { method: "DELETE" }),

  listAchievements: () => request<any[]>("/context/achievements"),
  createAchievement: (data: any) => request<any>("/context/achievements", { method: "POST", body: JSON.stringify(data) }),
  updateAchievement: (id: number, data: any) => request<any>(`/context/achievements/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAchievement: (id: number) => request<any>(`/context/achievements/${id}`, { method: "DELETE" }),

  getJobPreferences: () => request<any>("/context/job-preferences"),
  updateJobPreferences: (data: any) => request<any>("/context/job-preferences", { method: "PUT", body: JSON.stringify(data) }),

  // Templates
  listTemplates: () => request<any[]>("/templates"),
  createTemplate: (data: any) => request<any>("/templates", { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (id: number, data: any) => request<any>(`/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTemplate: (id: number) => request<any>(`/templates/${id}`, { method: "DELETE" }),

  // Contacts
  listContacts: () => request<any[]>("/contacts"),
  listContactsMetrics: () => request<any[]>("/contacts/metrics"),
  createContact: (data: any) => request<any>("/contacts", { method: "POST", body: JSON.stringify(data) }),
  updateContactStatus: (id: number, status: string) => request<any>(`/contacts/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
  deleteContact: (id: number) => request<any>(`/contacts/${id}`, { method: "DELETE" }),

  // Scrapers
  scrapeCareerPage: (url: string) => request<any>("/scrapers/career-page", { method: "POST", body: JSON.stringify({ url }) }),
  scrapeGithub: (username_or_repo: string) => request<any>("/scrapers/github", { method: "POST", body: JSON.stringify({ username_or_repo }) }),
  scrapeJobPortal: (url: string) => request<any>("/scrapers/job-portal", { method: "POST", body: JSON.stringify({ url }) }),
  scrapeLinkedin: (url: string) => request<any>("/scrapers/linkedin", { method: "POST", body: JSON.stringify({ url }) }),
  autoDiscoverJobs: () => request<any>("/scrapers/auto-discover", { method: "POST" }),
  enrichApollo: (first_name: string, last_name: string, company_domain: string) => request<any>("/scrapers/enrich/apollo", { method: "POST", body: JSON.stringify({ first_name, last_name, company_domain }) }),
  listScrapeQueue: () => request<any[]>("/scrapers/queue"),
  runNormalizer: () => request<any>("/scrapers/normalize", { method: "POST" }),

  // Send Queue & Approval
  listQueue: () => request<any[]>("/queue"),
  listGenericQueue: () => request<any[]>("/queue/generic"),
  personalizeContact: (id: number, template_id?: number) => request<any>(`/queue/${id}/personalize${template_id ? `?template_id=${template_id}` : ""}`, { method: "POST" }),
  approveQueueItem: (id: number) => request<any>(`/queue/${id}/approve`, { method: "POST" }),
  rejectQueueItem: (id: number) => request<any>(`/queue/${id}/reject`, { method: "POST" }),
  sendMailNow: (id: number) => request<any>(`/queue/${id}/send`, { method: "POST" }),

  // Auth additions
  getMe: () => request<any>("/auth/me"),
  logout: () => request<any>("/auth/logout", { method: "POST" }),
};
