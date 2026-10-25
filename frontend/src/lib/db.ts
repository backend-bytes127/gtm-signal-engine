import { execFile } from "child_process";
import path from "path";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const DB_PATH = path.join(PROJECT_ROOT, "data", "signal_engine.duckdb");
const PYTHON = path.join(PROJECT_ROOT, "venv", "bin", "python");

export function query<T = Record<string, unknown>>(sql: string): Promise<T[]> {
  const script = `
import duckdb, json, sys
conn = duckdb.connect('${DB_PATH}', read_only=True)
rows = conn.execute(sys.argv[1]).fetchall()
cols = [d[0] for d in conn.description]
conn.close()
print(json.dumps([dict(zip(cols, r)) for r in rows]))
`;

  return new Promise((resolve, reject) => {
    execFile(
      PYTHON,
      ["-c", script, sql],
      { timeout: 10000, maxBuffer: 10 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) return reject(new Error(stderr || error.message));
        try {
          resolve(JSON.parse(stdout));
        } catch {
          reject(new Error(`Failed to parse query result: ${stdout.slice(0, 200)}`));
        }
      }
    );
  });
}
