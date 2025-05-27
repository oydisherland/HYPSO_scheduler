import matplotlib.pyplot as plt
plt.rcParams["text.usetex"] = True

plt.plot([0, 1], [0, 1])
plt.title(r'Test of \LaTeX\ rendering')  # fixed
plt.xlabel(r'$x$')
plt.ylabel(r'$y$')
plt.show()
