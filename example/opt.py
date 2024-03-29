from typing import Any, Tuple

import torch
from transformers import OPTForCausalLM

from torch_model_info_collector import runtime
from torch_model_info_collector.module_collector import ModuleCollector


class OptCollector(ModuleCollector):
    def __init__(self):
        super().__init__()
        self.fc_sparsity_threshold = 0.001
        self.fc_sparsity = [0, 0]
        self.attn_sparsity_threshold = 0.1
        self.attn_sparsity = [0, 0]
        self.num_attention_heads = None
        self.fc_grid = []

    def get_head_summary(self, tensor, n_head=None, name=''):
        if n_head is not None:
            tensor = tensor.reshape((-1, tensor.shape[1], n_head, tensor.shape[2] // n_head))
            tensor_sum_in_pos = torch.sum(tensor.abs() > self.attn_sparsity_threshold, dim=(1, 2))
            # tensor_trans = norm_tensor.transpose(-1, -2)
            # tensor_trans = tensor_trans.sum(dim=-1)
            self.plt_grid(tensor_sum_in_pos, name, output_dir='output/opt')
        else:
            name = name + '.raw'

        tensor_data_info = self.tensor_data_info(tensor, name, self.attn_sparsity_threshold)
        # self.plt_hist(
        #     tensor.abs(), name,
        #     title=tensor_data_info['fmt'], output_dir='output/opt'
        # )
        self.attn_sparsity = self.update_attn_sparsity_from_tensor_data_info(self.attn_sparsity, tensor_data_info)

    def get_fc_act_summary(self, tensor: torch.Tensor, name=''):
        assert isinstance(tensor, torch.Tensor)
        tensor_count = torch.sum(tensor != 0, dim=0)

        tensor_data_info = self.tensor_data_info(tensor, name, self.fc_sparsity_threshold)
        self.plt_hist(
            tensor_count, name,
            title=tensor_data_info['fmt'], output_dir='output/opt'
        )
        self.fc_sparsity = self.update_attn_sparsity_from_tensor_data_info(self.fc_sparsity, tensor_data_info)

        self.plt_grid(tensor, name, output_dir='output/opt')

    def get_hook(self, name: str):
        assert self.num_attention_heads is not None
        super_hook = super().get_hook(name)

        def hook(module: torch.nn.Module, inputs: Tuple[Any], output):
            super_hook(module, inputs, output)
            if name.endswith('.self_attn.out_proj'):
                self.get_head_summary(inputs[0], self.num_attention_heads, name)
            # elif name.endswith('.self_attn.q_proj'):
            #     self.get_head_summary(output, None, name)
            # elif name.endswith('.self_attn.k_proj'):
            #     self.get_head_summary(output, None, name)
            # elif name.endswith('.self_attn.v_proj'):
            #     self.get_head_summary(output, None, name)
            elif name.endswith('.activation_fn'):
                self.get_fc_act_summary(output, name)

        return hook

    def register_hook(self, model):
        self.num_attention_heads = model.config.num_attention_heads
        super().register_hook(model)


def run_example():
    collector = runtime.run_module('facebook/opt-13b', OptCollector())
    assert OPTForCausalLM

    print(
        f'overall fc sparsity is {collector.fc_sparsity[0] / collector.fc_sparsity[1] :.2f} '
        f'== {collector.fc_sparsity}'
    )
    print(
        f'overall attn sparsity is {collector.attn_sparsity[0] / collector.attn_sparsity[1] :.2f} '
        f'== {collector.attn_sparsity}'
    )


def run_dataset():
    collector = runtime.run_module_dataset('facebook/opt-13b', OptCollector(), ('wikitext', 'wikitext-2-raw-v1', 'test'))
    assert OPTForCausalLM

    print(
        f'overall fc sparsity is {collector.fc_sparsity[0] / collector.fc_sparsity[1] :.2f} '
        f'== {collector.fc_sparsity}'
    )
    print(
        f'overall attn sparsity is {collector.attn_sparsity[0] / collector.attn_sparsity[1] :.2f} '
        f'== {collector.attn_sparsity}'
    )


if __name__ == '__main__':
    run_dataset()
