import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 자체 gzip 압축을 끈다 (2026-08-17).
  // 켜두면 Railway 엣지 프록시와 겹쳐 chunked 응답의 종료 청크(0\r\n\r\n)가 유실되고,
  // 엄격한 클라이언트(Chrome)가 net::ERR_INVALID_CHUNKED_ENCODING으로 페이지를 통째로 거부한다
  // (사파리·curl은 관대해서 정상으로 보여 발견이 늦었다). 압축은 Railway 엣지가 담당한다.
  // 근거: node_modules/next/dist/docs/.../next-config-js/compress.md — "프록시가 압축을 처리하면 false로"
  compress: false,
};

export default nextConfig;
