import { Router } from "express";
import { proxyComfy } from "@/utils/comfyProxy";
export default Router().get("/{*path}", proxyComfy);
