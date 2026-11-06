import { Router, raw } from "express";
import { proxyComfy } from "@/utils/comfyProxy";
export default Router().post("/{*path}", raw({ type: "multipart/form-data", limit: "100mb" }), proxyComfy);
