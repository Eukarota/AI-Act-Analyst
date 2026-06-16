# vLLM component (Shape B)

Opt-in Kustomize component for client missions running the **self-hosted
vLLM** shape (ADR 0005). The default prod overlay does NOT include this
component; the public demo runs on Mistral La Plateforme (Shape A).

## Activation checklist

1. **Terraform.** Flip `gpu_enabled = true` in
   `infra/terraform/environments/<env>/main.tfvars` and re-apply. This
   provisions an OVH GPU node pool attached to the Kapsule cluster with
   a `workload=vllm:NoSchedule` taint and a matching node label.

2. **NVIDIA device plugin.** Install the device plugin DaemonSet so
   `nvidia.com/gpu` shows up as a schedulable resource:

   ```bash
   kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.16.2/deployments/static/nvidia-device-plugin.yml
   ```

3. **Hugging Face token.** Mistral 7B Instruct is a gated repo. Accept
   the licence on huggingface.co and create a read-only token:

   ```bash
   kubectl -n boussole create secret generic vllm-secrets \
     --from-literal=HF_TOKEN=<your_hf_token>
   ```

4. **Include the component** from your overlay's `kustomization.yaml`:

   ```yaml
   components:
     - ../../components/vllm
   ```

5. **Point the backend at the in-cluster vLLM service.** Recreate or
   patch the runtime secret:

   ```bash
   kubectl -n boussole create secret generic boussole-backend-secrets \
     --from-literal=BOUSSOLE_DATABASE_URL=... \
     --from-literal=BOUSSOLE_LLM_URL=http://vllm.boussole.svc.cluster.local:8000 \
     --from-literal=BOUSSOLE_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3 \
     --from-literal=MISTRAL_API_KEY= \
     --dry-run=client -o yaml | kubectl apply -f -
   kubectl -n boussole rollout restart deploy/boussole-backend
   ```

6. **Wait on the first pull.** Initial pod startup downloads ~14 GB of
   model weights to the emptyDir cache. The readiness probe is tuned
   for ~2 minutes; the liveness probe waits 5 minutes before kicking
   in. Subsequent pod restarts on the same node reuse the cache.

## Switching back to Shape A

1. Recreate `boussole-backend-secrets` with `BOUSSOLE_LLM_URL=https://api.mistral.ai`, `BOUSSOLE_LLM_MODEL=mistral-large-latest`, and a populated `MISTRAL_API_KEY`.
2. Remove the `../../components/vllm` line from the overlay and re-apply.
3. Flip `gpu_enabled = false` in tfvars and re-apply Terraform; the GPU pool tears down and the bill returns to zero on that line.
