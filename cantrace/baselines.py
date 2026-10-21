"""Baselines trained on the identical normal-only subset as the MPS model."""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
import torch
from torch import nn
from .conditional import identifiers


class GRUAE(nn.Module):
    def __init__(self, features=22, window=4, hidden=24):
        super().__init__()
        self.features, self.window = features, window
        self.encoder = nn.GRU(features, hidden, batch_first=True)
        self.decoder = nn.Sequential(
            nn.Linear(hidden, 48), nn.ReLU(), nn.Linear(48, window * features)
        )

    def forward(self, x):
        _, h = self.encoder(x.reshape(-1, self.window, self.features))
        return self.decoder(h[-1])


def fit_baselines(x, window=4):
    torch.manual_seed(7)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pca = PCA(n_components=min(12, x.shape[1], len(x)), svd_solver="full").fit(x)
    forest = IsolationForest(n_estimators=100, random_state=7, n_jobs=1).fit(x)
    net = GRUAE(x.shape[1] // window, window)
    opt = torch.optim.Adam(net.parameters(), lr=0.003)
    xt = torch.tensor(x, dtype=torch.float32)
    for _ in range(30):
        for batch in xt.split(128):
            opt.zero_grad()
            loss = torch.mean((net(batch) - batch) ** 2)
            loss.backward()
            opt.step()
    net.eval()
    conditioned = {
        int(key): PCA(
            n_components=min(8, len(x[identifiers(x) == key]), x.shape[1]),
            svd_solver="full",
        ).fit(x[identifiers(x) == key])
        for key in set(identifiers(x))
    }
    return {
        "PCA": pca,
        "PCA per-ID": conditioned,
        "Isolation Forest": forest,
        "GRU autoencoder": net,
    }


def score(model, x):
    if isinstance(model, dict):
        ids = identifiers(x)
        output = np.ones(len(x))
        for key in set(ids):
            if int(key) in model:
                output[ids == key] = score(model[int(key)], x[ids == key])
        return output
    if isinstance(model, PCA):
        return np.mean((x - model.inverse_transform(model.transform(x))) ** 2, axis=1)
    if isinstance(model, IsolationForest):
        return -model.score_samples(x)
    with torch.no_grad():
        return np.concatenate(
            [
                torch.mean((model(b) - b) ** 2, dim=1).numpy()
                for b in torch.tensor(x, dtype=torch.float32).split(4096)
            ]
        )
