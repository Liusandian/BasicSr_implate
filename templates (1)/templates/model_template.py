"""
模型模板 - BasicSR

用于创建自定义训练模型

使用说明:
1. 复制此文件到 basicsr/models/ 目录
2. 重命名为 {yourmodel}_model.py
3. 修改类名和注册名
4. 实现训练逻辑
5. 在配置文件中使用 model_type: YourModel
"""

import torch
from collections import OrderedDict
from os import path as osp
from tqdm import tqdm

from basicsr.archs import build_network
from basicsr.losses import build_loss
from basicsr.metrics import calculate_metric
from basicsr.utils import get_root_logger, imwrite, tensor2img
from basicsr.utils.registry import MODEL_REGISTRY
from basicsr.models.base_model import BaseModel


# ============================================================================
# 示例 1: 简单的单网络模型（继承 BaseModel）
# ============================================================================

@MODEL_REGISTRY.register()
class SimpleModelTemplate(BaseModel):
    """
    简单模型模板 - 单网络训练

    适用于: 基础的图像处理任务（超分、去噪等）

    配置文件示例:
        model_type: SimpleModelTemplate

        network_g:
          type: SimpleNet
          num_in_ch: 3
          num_out_ch: 3

        train:
          optim_g:
            type: Adam
            lr: 0.0001

          pixel_opt:
            type: L1Loss
            loss_weight: 1.0
    """

    def __init__(self, opt):
        super(SimpleModelTemplate, self).__init__(opt)

        # ====== 1. 定义网络 ======
        self.net_g = build_network(opt['network_g'])
        self.net_g = self.model_to_device(self.net_g)
        self.print_network(self.net_g)

        # ====== 2. 加载预训练模型 ======
        load_path = self.opt['path'].get('pretrain_network_g', None)
        if load_path is not None:
            param_key = self.opt['path'].get('param_key_g', 'params')
            self.load_network(
                self.net_g,
                load_path,
                self.opt['path'].get('strict_load_g', True),
                param_key
            )

        # ====== 3. 初始化训练设置 ======
        if self.is_train:
            self.init_training_settings()

    def init_training_settings(self):
        """初始化训练设置（优化器、损失函数等）"""
        self.net_g.train()
        train_opt = self.opt['train']

        # ====== 定义损失函数 ======
        if train_opt.get('pixel_opt'):
            self.cri_pix = build_loss(train_opt['pixel_opt']).to(self.device)
        else:
            self.cri_pix = None

        if train_opt.get('perceptual_opt'):
            self.cri_perceptual = build_loss(train_opt['perceptual_opt']).to(self.device)
        else:
            self.cri_perceptual = None

        if self.cri_pix is None and self.cri_perceptual is None:
            raise ValueError('Both pixel and perceptual losses are None.')

        # ====== 设置优化器 ======
        self.setup_optimizers()

        # ====== 设置学习率调度器 ======
        self.setup_schedulers()

    def setup_optimizers(self):
        """设置优化器"""
        train_opt = self.opt['train']
        optim_params = []

        for k, v in self.net_g.named_parameters():
            if v.requires_grad:
                optim_params.append(v)
            else:
                logger = get_root_logger()
                logger.warning(f'Params {k} will not be optimized.')

        optim_type = train_opt['optim_g'].pop('type')
        self.optimizer_g = self.get_optimizer(
            optim_type,
            optim_params,
            **train_opt['optim_g']
        )
        self.optimizers.append(self.optimizer_g)

    def feed_data(self, data):
        """
        将数据送入模型

        Args:
            data (dict): 包含 'lq' 和 'gt' 的字典
        """
        self.lq = data['lq'].to(self.device)
        if 'gt' in data:
            self.gt = data['gt'].to(self.device)

    def optimize_parameters(self, current_iter):
        """
        优化网络参数（一个训练步骤）

        Args:
            current_iter (int): 当前迭代次数
        """
        # 前向传播
        self.optimizer_g.zero_grad()
        self.output = self.net_g(self.lq)

        # 计算损失
        l_total = 0
        loss_dict = OrderedDict()

        # 像素损失
        if self.cri_pix:
            l_pix = self.cri_pix(self.output, self.gt)
            l_total += l_pix
            loss_dict['l_pix'] = l_pix

        # 感知损失
        if self.cri_perceptual:
            l_percep, l_style = self.cri_perceptual(self.output, self.gt)
            if l_percep is not None:
                l_total += l_percep
                loss_dict['l_percep'] = l_percep
            if l_style is not None:
                l_total += l_style
                loss_dict['l_style'] = l_style

        # 反向传播
        l_total.backward()
        self.optimizer_g.step()

        self.log_dict = self.reduce_loss_dict(loss_dict)

    def test(self):
        """测试/推理"""
        self.net_g.eval()
        with torch.no_grad():
            self.output = self.net_g(self.lq)
        self.net_g.train()

    def dist_validation(self, dataloader, current_iter, tb_logger, save_img):
        """分布式验证"""
        if self.opt['rank'] == 0:
            self.nondist_validation(dataloader, current_iter, tb_logger, save_img)

    def nondist_validation(self, dataloader, current_iter, tb_logger, save_img):
        """非分布式验证"""
        dataset_name = dataloader.dataset.opt['name']
        with_metrics = self.opt['val'].get('metrics') is not None

        if with_metrics:
            if not hasattr(self, 'metric_results'):
                self.metric_results = {
                    metric: 0 for metric in self.opt['val']['metrics'].keys()
                }
            self._initialize_best_metric_results(dataset_name)
            self.metric_results = {metric: 0 for metric in self.metric_results}

        metric_data = dict()
        pbar = tqdm(total=len(dataloader), unit='image')

        for idx, val_data in enumerate(dataloader):
            img_name = osp.splitext(osp.basename(val_data['lq_path'][0]))[0]
            self.feed_data(val_data)
            self.test()

            visuals = self.get_current_visuals()
            sr_img = tensor2img([visuals['result']])
            metric_data['img'] = sr_img

            if 'gt' in visuals:
                gt_img = tensor2img([visuals['gt']])
                metric_data['img2'] = gt_img
                del self.gt

            # 保存图像
            if save_img:
                if self.opt['is_train']:
                    save_img_path = osp.join(
                        self.opt['path']['visualization'],
                        img_name,
                        f'{img_name}_{current_iter}.png'
                    )
                else:
                    save_img_path = osp.join(
                        self.opt['path']['visualization'],
                        dataset_name,
                        f'{img_name}.png'
                    )
                imwrite(sr_img, save_img_path)

            # 计算指标
            if with_metrics:
                for name, opt_ in self.opt['val']['metrics'].items():
                    self.metric_results[name] += calculate_metric(metric_data, opt_)

            pbar.update(1)
            pbar.set_description(f'Test {img_name}')
        pbar.close()

        if with_metrics:
            for metric in self.metric_results.keys():
                self.metric_results[metric] /= (idx + 1)
                self._update_best_metric_result(
                    dataset_name,
                    metric,
                    self.metric_results[metric],
                    current_iter
                )
            self._log_validation_metric_values(current_iter, dataset_name, tb_logger)

    def _log_validation_metric_values(self, current_iter, dataset_name, tb_logger):
        """记录验证指标"""
        log_str = f'Validation {dataset_name}\n'
        for metric, value in self.metric_results.items():
            log_str += f'\t # {metric}: {value:.4f}'
            if hasattr(self, 'best_metric_results'):
                log_str += (
                    f'\tBest: {self.best_metric_results[dataset_name][metric]["val"]:.4f} @ '
                    f'{self.best_metric_results[dataset_name][metric]["iter"]} iter'
                )
            log_str += '\n'

        logger = get_root_logger()
        logger.info(log_str)

        if tb_logger:
            for metric, value in self.metric_results.items():
                tb_logger.add_scalar(
                    f'metrics/{dataset_name}/{metric}',
                    value,
                    current_iter
                )

    def get_current_visuals(self):
        """获取当前可视化结果"""
        out_dict = OrderedDict()
        out_dict['lq'] = self.lq.detach().cpu()
        out_dict['result'] = self.output.detach().cpu()
        if hasattr(self, 'gt'):
            out_dict['gt'] = self.gt.detach().cpu()
        return out_dict

    def save(self, epoch, current_iter):
        """保存模型"""
        self.save_network(self.net_g, 'net_g', current_iter)
        self.save_training_state(epoch, current_iter)


# ============================================================================
# 示例 2: GAN 模型（双网络：生成器+判别器）
# ============================================================================

@MODEL_REGISTRY.register()
class GANModelTemplate(BaseModel):
    """
    GAN 模型模板

    适用于: 需要对抗训练的任务

    配置文件示例:
        model_type: GANModelTemplate

        network_g:
          type: MyGenerator

        network_d:
          type: MyDiscriminator

        train:
          optim_g:
            type: Adam
            lr: 0.0001

          optim_d:
            type: Adam
            lr: 0.0001

          gan_opt:
            type: GANLoss
            gan_type: vanilla
            loss_weight: 0.1
    """

    def __init__(self, opt):
        super(GANModelTemplate, self).__init__(opt)

        # 定义生成器
        self.net_g = build_network(opt['network_g'])
        self.net_g = self.model_to_device(self.net_g)
        self.print_network(self.net_g)

        # 定义判别器
        self.net_d = build_network(opt['network_d'])
        self.net_d = self.model_to_device(self.net_d)
        self.print_network(self.net_d)

        # 加载预训练模型
        load_path = self.opt['path'].get('pretrain_network_g', None)
        if load_path is not None:
            self.load_network(
                self.net_g,
                load_path,
                self.opt['path'].get('strict_load_g', True)
            )

        load_path = self.opt['path'].get('pretrain_network_d', None)
        if load_path is not None:
            self.load_network(
                self.net_d,
                load_path,
                self.opt['path'].get('strict_load_d', True)
            )

        if self.is_train:
            self.init_training_settings()

    def init_training_settings(self):
        """初始化训练设置"""
        self.net_g.train()
        self.net_d.train()
        train_opt = self.opt['train']

        # 损失函数
        if train_opt.get('pixel_opt'):
            self.cri_pix = build_loss(train_opt['pixel_opt']).to(self.device)
        else:
            self.cri_pix = None

        if train_opt.get('gan_opt'):
            self.cri_gan = build_loss(train_opt['gan_opt']).to(self.device)
        else:
            raise ValueError('GAN loss is required for GAN model.')

        # 优化器
        self.setup_optimizers()
        self.setup_schedulers()

    def setup_optimizers(self):
        """设置双优化器"""
        train_opt = self.opt['train']

        # 生成器优化器
        optim_type = train_opt['optim_g'].pop('type')
        self.optimizer_g = self.get_optimizer(
            optim_type,
            self.net_g.parameters(),
            **train_opt['optim_g']
        )
        self.optimizers.append(self.optimizer_g)

        # 判别器优化器
        optim_type = train_opt['optim_d'].pop('type')
        self.optimizer_d = self.get_optimizer(
            optim_type,
            self.net_d.parameters(),
            **train_opt['optim_d']
        )
        self.optimizers.append(self.optimizer_d)

    def feed_data(self, data):
        """送入数据"""
        self.lq = data['lq'].to(self.device)
        if 'gt' in data:
            self.gt = data['gt'].to(self.device)

    def optimize_parameters(self, current_iter):
        """优化参数（GAN 双优化器）"""
        # ====== 优化生成器 ======
        for p in self.net_d.parameters():
            p.requires_grad = False

        self.optimizer_g.zero_grad()
        self.output = self.net_g(self.lq)

        l_g_total = 0
        loss_dict = OrderedDict()

        # 像素损失
        if self.cri_pix:
            l_g_pix = self.cri_pix(self.output, self.gt)
            l_g_total += l_g_pix
            loss_dict['l_g_pix'] = l_g_pix

        # GAN 损失
        fake_g_pred = self.net_d(self.output)
        l_g_gan = self.cri_gan(fake_g_pred, True, is_disc=False)
        l_g_total += l_g_gan
        loss_dict['l_g_gan'] = l_g_gan

        l_g_total.backward()
        self.optimizer_g.step()

        # ====== 优化判别器 ======
        for p in self.net_d.parameters():
            p.requires_grad = True

        self.optimizer_d.zero_grad()

        # 真实样本
        real_d_pred = self.net_d(self.gt)
        l_d_real = self.cri_gan(real_d_pred, True, is_disc=True)
        loss_dict['l_d_real'] = l_d_real
        loss_dict['out_d_real'] = torch.mean(real_d_pred.detach())
        l_d_real.backward()

        # 假样本
        fake_d_pred = self.net_d(self.output.detach())
        l_d_fake = self.cri_gan(fake_d_pred, False, is_disc=True)
        loss_dict['l_d_fake'] = l_d_fake
        loss_dict['out_d_fake'] = torch.mean(fake_d_pred.detach())
        l_d_fake.backward()

        self.optimizer_d.step()

        self.log_dict = self.reduce_loss_dict(loss_dict)

    def test(self):
        """测试"""
        self.net_g.eval()
        with torch.no_grad():
            self.output = self.net_g(self.lq)
        self.net_g.train()

    def save(self, epoch, current_iter):
        """保存双网络"""
        self.save_network(self.net_g, 'net_g', current_iter)
        self.save_network(self.net_d, 'net_d', current_iter)
        self.save_training_state(epoch, current_iter)


# ============================================================================
# 使用建议
# ============================================================================

"""
1. 大多数情况下，可以直接继承现有模型:
   - SRModel: 标准超分任务
   - SRGANModel: 需要 GAN 的超分任务
   - VideoRecurrentModel: 视频超分任务

2. 只在以下情况创建新模型:
   - 训练流程有特殊需求（如多阶段训练）
   - 需要额外的网络（如多个生成器）
   - 验证流程需要定制

3. 模型继承层次:
   BaseModel
   ├── SRModel (单网络，像素损失)
   │   └── RealESRNetModel (特殊验证)
   ├── SRGANModel (GAN训练)
   │   ├── ESRGANModel (Relativistic GAN)
   │   └── RealESRGANModel (复杂退化)
   └── VideoBaseModel (视频基类)
       ├── VideoRecurrentModel (循环网络)
       └── VideoGANModel (视频GAN)
"""

