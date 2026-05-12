import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

type TopologyContract = {
  version?: string;
  topologies?: Record<
    string,
    {
      topology_class: string;
      frontend_origin: string;
      api_origin: string;
      nextauth_url: string;
    }
  >;
};

const DEFAULT_CONTRACT: Required<TopologyContract> = {
  version: "runtime_topology_v1",
  topologies: {
    local: {
      topology_class: "local",
      frontend_origin: "http://localhost:3000",
      api_origin: "http://localhost:8000",
      nextauth_url: "http://localhost:3000",
    },
    public: {
      topology_class: "public",
      frontend_origin: "https://lyraos.org",
      api_origin: "https://api.lyraos.org",
      nextauth_url: "https://lyraos.org",
    },
  },
};

function normalizeOrigin(value: string | undefined | null): string {
  return (value || "").trim().replace(/\/$/, "");
}

function loadContract(): Required<TopologyContract> {
  const candidates = [
    path.join(process.cwd(), "..", "runtime_topology.json"),
    path.join(process.cwd(), "runtime_topology.json"),
  ];
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) {
        return JSON.parse(fs.readFileSync(candidate, "utf8"));
      }
    } catch {
      // Fall through to the embedded contract. The endpoint should report
      // topology state even when the manifest is missing from a dev runtime.
    }
  }
  return DEFAULT_CONTRACT;
}

function requestOrigin(request: NextRequest): string {
  const host = request.headers.get("host") || request.nextUrl.host;
  if (host === "lyraos.org") return "https://lyraos.org";
  if (host?.startsWith("localhost") || host?.startsWith("127.0.0.1")) {
    return `http://${host}`;
  }
  return request.nextUrl.origin;
}

function topologyByFrontendOrigin(
  contract: Required<TopologyContract>,
  origin: string
): string | null {
  for (const [name, topology] of Object.entries(contract.topologies)) {
    if (normalizeOrigin(topology.frontend_origin) === normalizeOrigin(origin)) {
      return name;
    }
  }
  return null;
}

function topologyByCompiledRuntime(
  contract: Required<TopologyContract>,
  nextauthUrl: string,
  apiOrigin: string
): string | null {
  for (const [name, topology] of Object.entries(contract.topologies)) {
    if (
      normalizeOrigin(topology.nextauth_url) === normalizeOrigin(nextauthUrl) &&
      normalizeOrigin(topology.api_origin) === normalizeOrigin(apiOrigin)
    ) {
      return name;
    }
  }
  return null;
}

export function GET(request: NextRequest) {
  const contract = loadContract();
  const frontendOrigin = requestOrigin(request);
  const compiledApiOrigin = normalizeOrigin(
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  );
  const nextauthUrl = normalizeOrigin(
    process.env.NEXTAUTH_URL || "http://localhost:3000"
  );
  const expectedTopologyClass = topologyByFrontendOrigin(contract, frontendOrigin);
  const compiledTopologyClass = topologyByCompiledRuntime(
    contract,
    nextauthUrl,
    compiledApiOrigin
  );
  const verifiedTopology = Boolean(
    expectedTopologyClass &&
      compiledTopologyClass &&
      expectedTopologyClass === compiledTopologyClass
  );

  return NextResponse.json({
    topology_class: verifiedTopology ? expectedTopologyClass : "mixed",
    frontend_origin: frontendOrigin,
    compiled_api_origin: compiledApiOrigin,
    nextauth_url: nextauthUrl,
    build_id:
      process.env.NEXT_PUBLIC_BUILD_ID ||
      process.env.BUILD_ID ||
      process.env.VERCEL_GIT_COMMIT_SHA ||
      "dev",
    runtime_stamp: new Date().toISOString(),
    verified_topology: verifiedTopology,
    contract_version: contract.version,
    expected_topology_class: expectedTopologyClass,
    compiled_topology_class: compiledTopologyClass,
  });
}
