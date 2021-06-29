# Handling Long Sequences
- for the dummy experiment:
  * setting line 149 in Transformer.py to `max_len=4000` instead of the default 2500 worked
  * had to use `batch_size=1` for p2.xlarge (11.4 GB of GPU Memory)

## Thoughts for Future Actions
1. using larger instance with more memory might give cost-efficient boost in batch-size and hence train time
2. us Conformer to reduce memory need and to create shorter sequences instead 
