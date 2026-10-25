// Keep this optional frontend rooted in its own project even when the
// parent TBCare checkout has a separate package-lock.json.
// No remote backend, image source, or secret is configured here.
const nextConfig = {
  outputFileTracingRoot: process.cwd(),
};
export default nextConfig;
