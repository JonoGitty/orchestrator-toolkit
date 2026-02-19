import subprocess

def cleanup(plan):
    print("\n🧹 Cleaning up…")
    for step in plan.split('\n'):
        if "install" in step:
            pkg = step.split()[-1]
            cmd = f"sudo apt remove --purge -y {pkg}"
            print(f"▶ {cmd}")
            subprocess.run(cmd, shell=True)
    print("✅ Cleanup complete.")
