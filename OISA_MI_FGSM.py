import numpy as np
import random
import torch, torchvision
from torchvision.transforms import Resize

def loss_fun(model, x, y):
    p = model.net(x.to(model.device))
    loss = torch.nn.CrossEntropyLoss()(p, y.to(model.device))
    return loss

def SIM(model, images, labels):
    grad = torch.zeros(images.shape).type_as(images)
    trans_images = images.clone()
    a = 10
    rate = 1.1
    scales = [1,2,3,4,5]
    for scale in scales:
        noise = torch.distributions.gamma.Gamma(torch.ones(trans_images.shape), torch.tensor(rate)).sample().to('cuda')
        length = int(88*a/16)
        left = int((88-length)/2)
        right = int((88+length)/2)
        noise[:,:,left:right,left:right] = 1.0
        scales_images = trans_images * noise
        scales_images[:,1,:,:] = trans_images[:,1,:,:]
        scales_images = scales_images.detach()
        scales_images.requires_grad = True
        model.net.zero_grad()
        loss = loss_fun(model, scales_images, labels)
        loss.backward()
        grad = grad + scales_images.grad.data
    return grad

def my_mi_fgsm_attack(model, image, label, epsilon, num_iterations = 10, momentum=1):

    # Initialize the adversarial example to the input data
    image = image.to(model.device)
    alpha = epsilon / num_iterations
    adv_image = image + torch.Tensor(np.random.uniform(-alpha, alpha, image.shape)).type_as(image)
    g = torch.zeros(image.shape).type_as(image)

    # Loop over the number of iterations
    for _ in range(num_iterations):
        
        # Compute the gradient 
        adv_image = adv_image.detach()
        adv_image.requires_grad = True
        model.net.zero_grad()
        loss = loss_fun(model, adv_image, label)
        loss.backward()
        grad_0 = adv_image.grad.data

        # Scale Invariant
        total_grad = grad_0 + SIM(model, adv_image, label) 
        g = momentum * g + (total_grad/(torch.mean(torch.abs(total_grad), dim=(1,2,3), keepdim=True))).cuda()
        
        # Update the adversarial example
        sign_grad = g.sign()
        adv_image = adv_image + alpha * sign_grad

        adv_image[:,0,:,:] = torch.min(torch.max(adv_image[:,0,:,:], image[:,0,:,:] - epsilon), image[:,0,:,:] + epsilon)
        adv_image[:,1,:,:] = torch.min(torch.max(adv_image[:,1,:,:], image[:,1,:,:] - epsilon), image[:,1,:,:] + epsilon)

        adv_image[:,0,:,:] = torch.clamp(adv_image[:,0,:,:], torch.min(image[:,0,:,:]), torch.max(image[:,0,:,:]))
        adv_image[:,1,:,:] = torch.clamp(adv_image[:,1,:,:], torch.min(image[:,1,:,:]), torch.max(image[:,1,:,:]))
    # Return the adversarial example
    return adv_image
