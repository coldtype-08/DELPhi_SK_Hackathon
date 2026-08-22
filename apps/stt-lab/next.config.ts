import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 자체 gzip 압축을 끈다 (2026-08-17) — console과 동일한 이유.
  // Railway 엣지와 겹치면 chunked 종료 청크가 유실되어 Chrome이 페이지를 거부한다
  // (net::ERR_INVALID_CHUNKED_ENCODING). 압축은 Railway 엣지가 담당한다.
  compress: false,
};

export default nextConfig;
